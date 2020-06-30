from cCtrl import ModelControl
from cGeo import ModelGeoControl
from cEvents import ModelEvents
from config import *
import fileinput


class Hy2OptModel(ModelControl, ModelGeoControl, ModelEvents):
    # name = ReadOnlyParameter("model_name")
    # model_file = ReadOnlyParameter(dir2tf + "models/model_name.hy2model")

    def __init__(self, model_name):
        self._name = model_name
        self._model_file = dir2tf + "models/" + model_name + ".hy2model"
        self.logger = logging.getLogger("logfile")

        ModelControl.__init__(self)
        ModelGeoControl.__init__(self)
        ModelEvents.__init__(self)

        # Control par_group dicts
        self.tcf_applied_dict = {}
        self.sta_applied_dict = {}
        self.out_applied_dict = {}
        # Geo par_group dicts
        self.tgc_applied_dict = {}
        self.mat_applied_dict = {}
        self.tbc_applied_dict = {}
        # BC par_group dicts
        self.bce_applied_dict = {}
        # self.bat_applied_dict = {}

        self.par_dict = {"ctrl": self.tcf_applied_dict, "stab": self.sta_applied_dict, "out": self.out_applied_dict,
                         "gctrl": self.tgc_applied_dict, "gmat": self.mat_applied_dict, "gbc": self.tbc_applied_dict,
                         "bce": self.bce_applied_dict}
        self.default_dicts = {"ctrl": self.tcf_dict, "stab": self.sta_dict, "out": self.map_out_dict,
                              "gctrl": self.geo_tgc_dict, "gmat": self.geo_mat_dict, "gbc": self.geo_tbc_dict,
                              "bce": self.events}
        self.complete()

    @property
    def model_file(self):
        return self._model_file

    @model_file.setter
    def model_file(self, val):
        raise Exception("Read-only: Use Hy2OpModel.set_parameter_... instead.")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        raise Exception("Read-only: Use Hy2OpModel.set_parameter_... instead.")

    def complete(self):
        for par_group, par_dict in self.default_dicts.items():
            for par in par_dict.keys():
                self.par_dict[par_group].update({par: ""})

    def export_as_tf(self):
        """Export internal model to Tuflow model files"""
        msg = []
        # retrieve model values
        self.get_boundary_sa_names()
        self.get_boundary_bc_names()
        self.load_model()
        if os.path.isfile(dir2tf + "models/" + self.event_file[0]):
            self.events = fGl.dict_nested_read_from_file(dir2tf + "models/" + self.event_file[0])
        else:
            msg.append("WARNING: No events defined.")

        # Write Tuflow model files
        new = fGl.copy_tree(tf_source_tree, dir2tf + "user_models/" + str(self._name) + "/")
        msg.append(self.export_tgc())
        msg.append(self.export_tbc())
        msg.append(self.export_bce())
        msg.append(self.export_bcm())
        msg.append(self.export_tef())
        # msg.append(self.export_mat())
        msg.append("\nFinished writing Tuflow model files for {0}\n".format(str(self._name)))
        print(*msg, sep='\n')

    def export_tcf(self):
        tcf_file_name = os.path.join(dir2tf + "user_models/", "{0}/runs/{0}.tcf".format(self._name))
        try:
            with open(tcf_file_name, "w") as tcf_file:
                pass
        except:
            return "ERROR: Close file %s and re-run." % tcf_file_name

    def export_tef(self):
        tef_file_name = os.path.join(dir2tf + "user_models/", "{0}/runs/{0}.tef".format(self._name))
        try:
            with open(tef_file_name, "w") as tef_file:
                for e, e_defs in self.events.items():
                    # get outlet WSEs
                    outlets = [bc for bc in self.bc_dict['bc']]
                    outlet_wses = [e_defs[outlet] for outlet in outlets]
                    tef_file.write("Define Event == {0}\n\t"
                                   "BC Event Source == __event__ | {0}\n\t"
                                   "SET IWL == {1}\n\t"
                                   "Start Map Output == {2}\n\t"
                                   "End Time == {3}\n"
                                   "End Define\n".format(e, min(outlet_wses), 100 - 1, 100))
                return str(self._name + ".tef created")
        except:
            return "ERROR: Close file %s and re-run." % tef_file_name

    def export_bce(self):
        """Export event-specific bc file"""
        for e, e_defs in self.events.items():
            bce_file_name = dir2tf + "user_models/" + self._name + "/bc_dbase/2d_bc_" + str(e) + ".csv"
            if os.path.isfile(bce_file_name):
                fGl.rm_file(bce_file_name)
            try:
                bce_file = open(bce_file_name, "w")
            except:
                return "ERROR: Close " + bce_file_name + " an re-run model generator."
            bce_file.write("Name,Source,Column 1,Column 2\n")
            for sa in e_defs.keys():
                bce_file.write("{0},{1}_bc_data.csv,Time,{0}\n".format(sa, self._name))
            bce_file.truncate()
        return "2d_bc_EVENT files created"

    def export_bcm(self):
        """Export model-specific bc def"""
        start_time = 0
        end_time = 1000
        for e, e_defs in self.events.items():
            mbc_file_name = dir2tf + "user_models/{0}/bc_dbase/{0}_bc_data_{1}.csv".format(self._name, e)
            if os.path.isfile(mbc_file_name):
                fGl.rm_file(mbc_file_name)
            try:
                bcm_file = open(mbc_file_name, "w")
            except:
                return "ERROR: Close " + mbc_file_name + " an re-run model generator."
            col_names = ["Time"] + self.bc_dict['sa'] + self.bc_dict['bc']
            bcm_file.write(",".join(col_names) + "\n")
            bcm_file.write(",".join([str(start_time)] + [e_defs[col] for col in col_names[1:]]) + "\n")
            bcm_file.write(",".join([str(end_time)] + [e_defs[col] for col in col_names[1:]]))
            bcm_file.truncate()
        return str(self._name + "_bc_data files created")

    def export_tbc(self):
        tbc_file_name = dir2tf + "user_models/{0}/model/{0}.tbc".format(self._name)
        if os.path.isfile(tbc_file_name):
            fGl.rm_file(tbc_file_name)
        with open(tbc_file_name, "w") as tbc_file:
            for par, val in self.par_dict["gbc"].items():
                self.export_par(tbc_file, par, val)
            tbc_file.truncate()
        return str(self._name + ".tbc file created")

    def export_tgc(self):
        """Write Tuflow .tgc file"""
        tgc_file_name = dir2tf + "user_models/{0}/model/{0}.tgc".format(self._name)
        if os.path.isfile(tgc_file_name):
            fGl.rm_file(tgc_file_name)
        with open(tgc_file_name, "w") as tgc_file:
            for par, val in self.par_dict["gctrl"].items():
                self.export_par(tgc_file, par, val)

            self.export_par(tgc_file, "stab", "Cell Size")

            for par, val in self.par_dict["gmat"].items():
                self.export_par(tgc_file, par, val)

        return str(self._name + ".tgc file created")

    def export_par(self, f, par, val):
        """
        Parses parameter and value and appends to file f in Tuflow format  {par} == {val}
        :param f: opened file object
        :param par: STR, dict key
        :param val: corresponding dict val
        """
        if par == "Read GIS Mat" and val == "":
            print("Missing GIS Mat file (OK if uniform Manning\'s n applied) ...")
            return
        if par.startswith("Read"):
            if val == "":
                print("ERROR: Missing file definition for {0}.".format(par))
                return
            val = self.par2tf_path(par, val)
        if type(val) == tuple:
            val = str(val)[1:-1]
        if val != "":
            f.write("{0} == {1}\n".format(par, val))
        else:
            print("ERROR: Missing parameter: {0}.".format(par))

    @chk_osgeo
    def get_boundary_bc_names(self):
        dir2bc_shp = self.get_model_par("gbc", "Read GIS BC")
        field_names = fGl.get_shp_field_names(dir2bc_shp)
        try:
            the_field_name = [x for x in field_names if ("name" in x.lower())][0]
        except:
            return "Field NAME is not defined in Read GIS SA: 2d_sa_MODEL_QT_R.shp"
        self.bc_dict['bc'] = fGl.get_shp_field_values(dir2bc_shp, the_field_name)
        for bc in self.bc_dict['bc']:
            self.events[self.event_0].update({bc: 0.0})
        self.event_file = [self.name + ".events"]
        try:
            # events-dict is initiated with a 0-None entry that needs to be removed
            del self.events[self.event_0][0]
        except:
            pass

    @chk_osgeo
    def get_boundary_sa_names(self):
        dir2sa_shp = self.get_model_par("gbc", "Read GIS SA")
        field_names = fGl.get_shp_field_names(dir2sa_shp)
        try:
            the_field_name = [x for x in field_names if ("name" in x.lower())][0]
        except:
            return "Field NAME is not defined in Read GIS SA: 2d_sa_MODEL_QT_R.shp"
        self.bc_dict['sa'] = fGl.get_shp_field_values(dir2sa_shp, the_field_name)
        for sa in self.bc_dict['sa']:
            self.events[self.event_0].update({sa: 0.0})
        self.event_file = [self.name + ".events"]
        try:
            # events-dict is initiated with a 0-None entry that needs to be removed
            del self.events[self.event_0][0]
        except:
            pass

    def get_model_par(self, par_group, par):
        """get model parameter from model file"""
        try:
            for line in open(self.model_file, "r").readlines():
                if line.strip().startswith("{0}::{1}::".format(par_group, par)):
                    par_val_str = str(line.strip().split("::")[-1])
                    if "," in par_val_str:
                        return fGl.str2tuple(par_val_str)
                    if "." in par_val_str:
                        try:
                            return float(par_val_str)
                        except ValueError:
                            pass
                    try:
                        return int(par_val_str)
                    except ValueError:
                        return par_val_str
            return self.default_dicts[par_group][par][0]  # else: return default value
        except:
            self.logger.error("Could not retrieve model value (par_group={0}, par={1})".format(str(par_group), str(par)))

    def load_model(self):
        """load model parameters from model file"""
        for par_group, par_dict in self.par_dict.items():
            for par in par_dict.keys():
                par_dict[par] = self.get_model_par(par_group, par)

    def overwrite_defaults(self, par_group):
        if os.path.isfile(self.model_file):
            for par in self.default_dicts[par_group].keys():
                self.default_dicts[par_group][par][0] = self.get_model_par(par_group, par)

    def par2tf_path(self, par, val):
        par = str(par)
        i_val = str(val)
        if "Read Materials File" in par:
            i_val = "..\\model\\" + i_val.split("\\")[-1].split('/')[-1]
        if i_val.endswith(".shp"):
            i_val = "..\\model\\gis\\" + i_val.split("\\")[-1].split('/')[-1]
        if i_val.endswith(".asc") or i_val.endswith(".flt"):
            i_val = "..\\model\\grid\\" + i_val.split("\\")[-1].split('/')[-1]
        file_target = dir2tf + "user_models\\%s%s" % (self._name, i_val.strip("."))
        if not os.path.isfile(file_target):
            shutil.copyfile(val, file_target)
        return i_val

    def replace_model_par(self, search_pattern, new_line_str):
        """
        Replace lines that start with a pattern
        :param search_pattern: STR
        :param new_line_str: STR
        """
        for line in fileinput.input([self.model_file], inplace=True):
            if line.strip().startswith(search_pattern):
                line = new_line_str
            sys.stdout.write(line)

    def run_model(self, tf_dir):
        """Run Tuflow model"""
        commands = ["Set TF_EXE={0}".format(tf_dir)]

        for e, e_defs in self.events.items():
            print(e)
            print(e_defs)
            command = ""
            commands.append(command)

        for command in commands:
            print(command)
            os.system(command)

    def save_model(self):
        for par_group, par_dict in self.par_dict.items():
            for par in par_dict.keys():
                self.write_parameter(par_group, par)
            self.sign_model(par_group)

    def set_model_name(self, model_name):
        self._name = model_name
        self._model_file = dir2tf + "models/" + model_name + ".hy2model"

    def set_usr_parameters(self, par_group, par, values):
        """
        Writes user values in par_dict
        :param par_group: STR corresponding to self.par_dict.keys()
        :param par: STR corresponding to self.par_dict.keys()
        :param values: LIST with one or more values to be written in one line of a (TCF/TGC/TBC/TEF) file
        :return: None
        """
        if values.__len__() > 1:
            val_str = " ".join(values)
        else:
            val_str = str(values[0])
        self.par_dict[par_group][par] = val_str
        self.write_parameter(par_group, par)

    def sign_model(self, par_group):
        """ Model signature that tells the model that parameters for par_group were already written once. """
        f_model = open(self.model_file, "a+")
        if not (par_group + "::signature::True" in open(self.model_file).read()):
            f_model.write(par_group + "::signature::True\n")
            f_model.truncate()

    def signature_verification(self, par_group):
        if os.path.isfile(self.model_file):
            if par_group + "::signature::True" in open(self.model_file).read():
                return True
            else:
                if (par_group == "bce") and ("gbc::signature::True" in open(self.model_file).read()):
                    return True
        return False  # all other ...

    def write_parameter(self, par_group, par):
        write_str = "{0}::{1}::".format(par_group, par)
        if os.path.isfile(self.model_file):
            if write_str in open(self.model_file).read():
                self.replace_model_par(write_str, write_str + self.par_dict[par_group][par] + "\n")
                return 0
            f_model = open(self.model_file, "a+")
        else:
            f_model = open(self.model_file, "w")
        # f_model.seek(0)
        f_model.write(write_str + self.par_dict[par_group][par] + "\n")
        f_model.truncate()

    def __call__(self, *args, **kwargs):
        print("Class Info: <type> = Hy2OptModel (Tuflow) (%s)" % os.path.dirname(__file__))
        print(dir(self))

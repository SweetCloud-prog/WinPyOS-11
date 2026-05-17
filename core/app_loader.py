import os, json, importlib.util, sys


class AppLoader:
    def __init__(self):
        self.apps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps")
        self.apps = {}

    def scan_apps(self):
        self.apps = {}
        if not os.path.exists(self.apps_dir):
            return
        for item in sorted(os.listdir(self.apps_dir)):
            ap = os.path.join(self.apps_dir, item)
            mf = os.path.join(ap, "manifest.json")
            py = os.path.join(ap, "app.py")
            if os.path.isdir(ap) and os.path.exists(mf) and os.path.exists(py):
                try:
                    with open(mf, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    aid = m.get("id", item)
                    self.apps[aid] = {
                        "id": aid, "name": m.get("name", item),
                        "icon_name": m.get("icon_name", "file"),
                        "description": m.get("description", ""),
                        "path": ap, "module_path": py,
                    }
                except Exception as e:
                    print(f"[AppLoader] {item}: {e}")

    def get_app_list(self):
        return list(self.apps.values())

    def get_app_info(self, aid):
        return self.apps.get(aid)

    def load_app(self, aid, fs=None):
        info = self.apps.get(aid)
        if not info:
            return None
        try:
            if info["path"] not in sys.path:
                sys.path.insert(0, info["path"])
            spec = importlib.util.spec_from_file_location(f"app_{aid}_{id(info)}", info["module_path"])
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "App"):
                try:
                    return mod.App(file_system=fs)
                except TypeError:
                    return mod.App()
        except Exception as e:
            print(f"[AppLoader] Error {aid}: {e}")
            import traceback; traceback.print_exc()
        return None
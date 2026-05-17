import os, shutil
from datetime import datetime


class FileSystem:
    def __init__(self):
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_data")
        for d in ["Desktop","Documents","Downloads","Pictures","Music","Videos"]:
            os.makedirs(os.path.join(self.base_path, d), exist_ok=True)

    def get_base_path(self):
        return self.base_path

    def get_path(self, rel=""):
        full = os.path.normpath(os.path.join(self.base_path, rel))
        return full if full.startswith(self.base_path) else self.base_path

    def list_dir(self, rel=""):
        fp = self.get_path(rel)
        items = []
        if os.path.isdir(fp):
            try:
                for n in sorted(os.listdir(fp)):
                    p = os.path.join(fp, n)
                    s = os.stat(p)
                    items.append({"name":n,"is_dir":os.path.isdir(p),
                        "size":s.st_size if os.path.isfile(p) else 0,
                        "modified":datetime.fromtimestamp(s.st_mtime).strftime("%d/%m/%Y %H:%M"),
                        "path":os.path.relpath(p, self.base_path)})
            except PermissionError: pass
        items.sort(key=lambda x:(not x["is_dir"], x["name"].lower()))
        return items

    def create_file(self, rel, content=""):
        fp = self.get_path(rel)
        if fp.startswith(self.base_path):
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp,"w",encoding="utf-8") as f: f.write(content)

    def create_dir(self, rel):
        fp = self.get_path(rel)
        if fp.startswith(self.base_path):
            os.makedirs(fp, exist_ok=True)

    def read_file(self, rel):
        fp = self.get_path(rel)
        if os.path.isfile(fp):
            try:
                with open(fp,"r",encoding="utf-8") as f: return f.read()
            except: pass
        return None

    def delete(self, rel):
        fp = self.get_path(rel)
        if fp == self.base_path or not fp.startswith(self.base_path): return
        try:
            if os.path.isdir(fp): shutil.rmtree(fp)
            elif os.path.isfile(fp): os.remove(fp)
        except: pass

    def rename(self, rel, new):
        fp = self.get_path(rel)
        if fp.startswith(self.base_path) and fp != self.base_path:
            try: os.rename(fp, os.path.join(os.path.dirname(fp), new))
            except: pass
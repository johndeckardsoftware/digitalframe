import os
from watchdog.observers import Observer
from watchdog.observers.api import EventQueue
from watchdog.events import FileSystemEventHandler
from dfitems import DFItemList

class  FolderChangeHandler(FileSystemEventHandler):
    def __init__(self, items: DFItemList):
        self.items = items
        self.reload_items = False

    def check(self, event):
        #print(f'{event.event_type=}, {event.src_path=}, {event.dest_path=}')
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            for k, v in self.items.type_ext.items():
                if ext in v.get('ext'):
                    if k == 'image':
                        self.reload_items = True
                    elif k == 'video':
                        self.reload_items = True
        if self.reload_items:
            self.items.load_items()
            self.reload_items = False

    def on_created(self, event):
        self.check(event)

    def on_deleted(self, event):
        self.check(event)
    
    def on_modified(self, event):
        self.check(event)
    
    def on_moved(self, event):
        self.check(event)
    

class FolderWatch:
    def __init__(self, items: DFItemList):
        self.items = items
        self.paths = items.paths
        self.observers = []
        self.event_handler = FolderChangeHandler(self.items)
        for path in self.paths:
            if os.path.exists(path):
                observer = Observer()
                observer.schedule(self.event_handler, path=path, recursive=True)
                observer.start()
                self.observers.append(observer)


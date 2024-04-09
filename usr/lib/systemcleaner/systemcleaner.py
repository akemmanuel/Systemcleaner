#!/usr/bin/python3
import gi
import subprocess as sub
import os
import psutil
from threading import Thread
import time

# Import GTK modules
gi.require_version("XApp", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, XApp, GLib

class FileChooser:
    """
    This class is an implementation for selecting a folder and scanning its contained files. It utilizes the GTK library and loads a Glade file for the user interface. The "searchfolder" method recursively scans files in the selected folder, collecting information such as file paths and sizes. The progress bar is updated during this process. The "start" method is triggered when the "start_session" button is clicked, calling the folder search on the selected directory.
    """
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("/usr/share/systemcleaner/systemcleaner.glade")
        self.window1 = self.builder.get_object("window1")
        self.window1.set_title("Ordner Auswählen")
        self.window1.connect("delete-event", Gtk.main_quit)
        self.window1.show()
        self.progress = self.builder.get_object("scan_progress")
        self.progress.set_visible(False)
        self.scan_text = self.builder.get_object("scan_text")
        self.builder.get_object("start_session").connect("clicked", self.start)

    def searchfolder(self, ordner):
        self.progress.set_visible(True)
        self.builder.get_object("scan_ordner").set_visible(False)
        self.builder.get_object("start_session").set_visible(False)
        self.scan_text.set_visible(False)
        end = []
        for verzeichnisname, unterordnerliste, dateiliste in os.walk(ordner):
            for datei in dateiliste:
                datei_pfad = os.path.join(verzeichnisname, datei)
                if os.path.isfile(datei_pfad):
                    end.append(datei_pfad)
        print("1%", end="\r")
        alles = len(end)
        schon = 0
        toreturn = []
        for e in end:
            try:
                toreturn.append({"datei_pfad": e, "datei_größe": os.path.getsize(e)})
                schon += 1
                fraction = 1 / alles * schon
                self.update_progress(fraction)
                Gtk.main_iteration_do(False)
                print(f"{round(100/alles*schon, 2)}%", end="\r")
            except Exception as e:
                schon += 1
                fraction = 1 / alles * schon
                self.update_progress(fraction)
                Gtk.main_iteration_do(False)
                print(f"{round(100/alles*schon, 2)}% {str(e)}")
        self.window1.destroy()
        Systemcleaner(toreturn)

    def update_progress(self, fraction):
        self.progress.set_fraction(fraction)

    def start(self, widget):
        folder = self.builder.get_object("scan_ordner").get_files()[0].get_path()
        self.searchfolder(folder)

class Systemcleaner():
    """
    This class opens a GTK application for system cleaning. It initializes the user interface, manages various UI elements, and provides functionality for tasks such as uninstalling programs and cleaning up large files. The class employs threads for asynchronous data fetching and updates. Additionally, it utilizes a custom script for advanced cleaning tasks with elevated privileges.
    """
    def __init__(self, files):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("/usr/share/systemcleaner/systemcleaner.glade")
        self.window2 = self.builder.get_object("window2")
        self.window2.set_title("Systemcleaner")
        self.window2.connect("delete-event", Gtk.main_quit)
        self.window2.show()
        
        # Variables
        self.files = files
        self.große = False
        self.leere = False

        # Gtk Elements
        self.smart_stack = self.builder.get_object("smart_stack")
        self.stack = self.builder.get_object("stack")
        self.smart_trash = self.builder.get_object("trash")
        self.smart_cache = self.builder.get_object("cache")
        self.smart_shutdown = self.builder.get_object("shutdown")
        self.smart_requ = self.builder.get_object("notrequiredfiles")
        self.smart_appcache = self.builder.get_object("appcache")

        # Buttons
        self.builder.get_object("smart_scan_home").connect("clicked", self.smart_scan)
        self.builder.get_object("start_scan").connect("clicked", self.start_smart_scan)
        self.builder.get_object("caches_next").connect("clicked", self.caches_next)
        self.builder.get_object("big_files_scan_next").connect("clicked", self.big_files_scan_next)
        self.builder.get_object("go_to_smart_home").connect("clicked", self.go_to_smart_home)

        #
        self.smart_stack.set_visible_child_name("home")

        # Speicherplatzinformationen abrufen
        disk_usage = psutil.disk_usage('/')
        free_space = disk_usage.free / (2**30)   # Freier Speicherplatz
        self.builder.get_object("free").set_text(f"Freier Speicher: {round(free_space, 1)}GB")

        self.window2.show()
        

        thread = Thread(target=self.großedaten)
        thread.start()
        thread.join()

        thread2 = Thread(target=self.getprogramms)
        thread2.start()
        thread2.join()

        thread3 = Thread(target=self.leeredaten)
        thread3.start()


    class TreeViewGtkWi():
        def __init__(self, tree_view: Gtk.TreeView, list_store: Gtk.ListStore, selection_mode: Gtk.SelectionMode, column, what = [["File", True],  ["Size", True]]):
            tree_view.set_model(list_store)

            self.column_check_box = Gtk.TreeViewColumn("Löschen")
            tree_view.append_column(self.column_check_box)

            self.cell = Gtk.CellRendererToggle()
            self.column_check_box.pack_start(self.cell, False)
            self.column_check_box.add_attribute(self.cell, "active", 0)
            self.cell.connect("toggled", self.on_cell_toggled, list_store)

            renderer = Gtk.CellRendererText()

            a = 1
            for i in what:
                self.column_file = Gtk.TreeViewColumn(i[0], renderer, text=a)
                if i[1]:
                    self.column_file.set_sort_column_id(a)

                tree_view.append_column(self.column_file)

                a += 1


            tree_view.get_selection().set_mode(selection_mode)
            tree_view.set_search_column(column)


        def on_cell_toggled(self, widget, path, list_store):
            iter = list_store.get_iter_from_string(path)
            list_store[iter][0] = not list_store[iter][0]


    def sorti(self, e):
        return e["datei_größe"]
        
    def nodisplay(self, widget, *data):
        file, box = data[0], data[1]
        if not os.path.isfile(os.path.expanduser("~/.systemcleaner-nodisplay")):
            nodisplay = open(os.path.expanduser("~/.systemcleaner-nodisplay"), "w")
            nodisplay.write("")
            nodisplay.close()
        nodisplay = open(os.path.expanduser("~/.systemcleaner-nodisplay"), "a+")
        nodisplay.write(f"{file}\n")
        nodisplay.close()
        box.destroy()

    
    def getprogramms(self):
        programms_o = sub.getoutput("apt list --installed")
        programms_a = programms_o.split("\n")
        programms = []
        for line in programms_a:
            programms.append(line.split("/")[0])

        programms = programms[4:]

        store = Gtk.ListStore(bool, str)
        treeview = self.builder.get_object("uninstall_programms")

        for program in programms:
            store.append([False, program])

        self.TreeViewGtkWi(treeview, store, Gtk.SelectionMode.NONE, 1, what=[["Name", True]])
        self.builder.get_object("uninstall").connect("clicked", self.uninstall, store, programms)
    
    def uninstall(self, widget, programs, real):
        items_to_remove = []
        a = 0
        for row in programs:
            if row[0]:
                items_to_remove.append([row[1], row.iter, a])
            a += 1
        for item in items_to_remove:
            text = sub.getoutput(f"pkexec apt-get remove -y {item[2]}")
            print(text)
                    
    def leeredaten(self):
        if not os.path.isfile(os.path.expanduser("~/.systemcleaner-nodisplay")):
            nodisplay = open(os.path.expanduser("~/.systemcleaner-nodisplay"), "w")
            nodisplay.write("")
            nodisplay.close()
        nodisplay = open(os.path.expanduser("~/.systemcleaner-nodisplay"), "r").read()
        end = []
        for datei in self.files:
            try:
                if datei["datei_größe"] <= 0:
                    end.append({"datei_pfad": datei["datei_pfad"], "datei_größe": datei["datei_größe"]})
            except:
                pass
        
        if self.leere == False:
            self.leere = True
            treeview = self.builder.get_object("empty_tree")
            store = Gtk.ListStore(bool, str, str)
            for file in end:
                store.append([False, file["datei_pfad"], str(round(file["datei_größe"] / 1000000000, 1))])

            self.TreeViewGtkWi(treeview, store, Gtk.SelectionMode.NONE, 1, what=[["File", True]])
            self.builder.get_object("delete_empty_files").connect("clicked", self.delete_files_from_store, store)

    def großedaten(self):
        if not os.path.isfile(os.path.expanduser("~/.systemcleaner-nodisplay")):
            nodisplay = open(os.path.expanduser("~/.systemcleaner-nodisplay"), "w")
            nodisplay.write("")
            nodisplay.close()
        nodisplay = open(os.path.expanduser("~/.systemcleaner-nodisplay"), "r").read()
        große_daten = self.files
        große_daten.sort(key=self.sorti, reverse=True)

        if self.große == False:
            self.große = True
            treeview = self.builder.get_object("big_tree")
            treeview2 = self.builder.get_object("smart_big_files_treeview")

            store = Gtk.ListStore(bool, str, str)
            self.store2 = Gtk.ListStore(bool, str, str)

            for file in große_daten:
                if file["datei_größe"] / 1000000000 >= 0.01:
                    store.append([False, file["datei_pfad"], str(round(file["datei_größe"] / 1000000000, 1))])
                if file["datei_größe"] / 1000000000 >= 0.5:
                    self.store2.append([False, file["datei_pfad"], str(round(file["datei_größe"] / 1000000000, 1))])

            self.TreeViewGtkWi(treeview, store, Gtk.SelectionMode.SINGLE, 0, what=[["File", True], ["Size", True]])
            self.TreeViewGtkWi(treeview2, self.store2, Gtk.SelectionMode.SINGLE, 0, what=[["File", True], ["Size", True]])

            self.builder.get_object("delete_big_files").connect("clicked", self.delete_files_from_store, store)

    def delete_files_from_store(self, widget, store):
        items_to_remove = []
        for row in store:
            if row[0]:
                items_to_remove.append([row[1], row.iter])

        for item in items_to_remove:
            os.remove(item[0])
            store.remove(item[1])
    
    def smart_scan(self, widget):
        self.stack.set_visible_child_name("smart_scan")

    def pkexec_dialog(self, list, code, errors=True):
        if code in list:
            title = list[code][0]
            text = list[code][1]
            s_text = list[code][2]
            dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.INFO)
            dialog.set_transient_for(self.window2)
            dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            dialog.set_title(title)
            dialog.set_property("text", text)
            dialog.format_secondary_text(s_text)
            dialog.show()
            dialog.run()
            dialog.destroy()
        else:
            if errors:
                title = "Eine Komische Fehlermeldung!"
                text = "Eine Komische Fehlermeldung!"
                s_text = "Fehler code: " + str(code)
                dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.INFO)
                dialog.set_transient_for(self.window2)
                dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
                dialog.set_title(title)
                dialog.set_property("text", text)
                dialog.format_secondary_text(s_text)
                dialog.show()
                dialog.run()
                dialog.destroy()

    def start_smart_scan(self, widget):
        self.smart_stack.set_visible_child_name("caches")
    
    def caches_next(self, widget):
        self.smart_stack.set_visible_child_name("bigfiles")

    def big_files_scan_next(self, widget):
        command = ""
        
        do = False
        if self.smart_trash.get_active():
            command += f"rm -rf {os.path.expanduser('~/.local/share/Trash/*')}\n"
            do = True
        if self.smart_cache.get_active():
            command += "rm /var/cache/apt/archives/*.deb\n"
            do = True
        if self.smart_shutdown.get_active():
            command += "rm /var/lib/systemd/coredump/core.*.zst\njournalctl --rotate\njournalctl --vacuum-time=2s\n"
            do = True
        if self.smart_appcache.get_active():
            command += f"rm -rf {os.path.expanduser('~/.cache/*')}\n"
            do = True
        if self.smart_requ.get_active():
            command += "apt autoremove"
            do = True
            
        if do:
            with open("/tmp/custom_script.sh", "w") as file:
                file.write(command)
                file.close()

                sub.run(["chmod", "+x", "/tmp/custom_script.sh"])
                result = sub.run(["pkexec", "bash", "-c", "/tmp/custom_script.sh"])
                returncode = result.returncode
                list = {127: ["Ein Fehler ist aufgetreten", "Ein Fehler ist aufgetreten", "Fehler: Falsches Passwort"], 126: ["Ein Fehler ist aufgetreten", "Ein Fehler ist aufgetreten", "Fehler: Abgebrochen"]}
                self.pkexec_dialog(list, returncode, errors=False)

        items_to_remove = []
        for row in self.store2:
            if row[0]:
                items_to_remove.append([row[1], row.iter])

        for item in items_to_remove:
            os.remove(item[0])
            self.store2.remove(item[1])

        self.smart_trash.set_active(False)
        self.smart_cache.set_active(False)
        self.smart_shutdown.set_active(False)
        self.smart_requ.set_active(False)

        self.smart_stack.set_visible_child_name("finish")

    def go_to_smart_home(self, widget):
        self.smart_stack.set_visible_child_name("home")

if __name__ == "__main__":
    FileChooser()
    Gtk.main()
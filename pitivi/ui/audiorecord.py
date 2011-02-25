import tempfile
import os
import shutil

import gst
import gtk

from fvumeter import FVUMeter
ui = """
 <interface>
  <requires lib="gtk+" version="2.16"/>
     <object class="GtkButton" id="record_button">
        <property name="visible">True</property>
        <property name="sensitive">False</property>
        <property name="can_focus">True</property>
        <property name="receives_default">True</property>
        <property name="relief">none</property>
        <child>
          <object class="GtkImage" id="button_image">
            <property name="visible">True</property>
            <property name="stock">gtk-media-record</property>
          </object>
        </child>
      </object>
      </interface>
"""

def clamp(x, min, max):
    if x < min:
        return min
    elif x > max:
        return max
    return x

class AudioRecorder(gtk.HBox):
    def __init__(self, instance):
        gtk.HBox.__init__(self)
        
        self.app = instance

        self.audiosrc = gst.element_factory_make("autoaudiosrc", "audiosrc")
        self.level = gst.element_factory_make("level", "level")
        self.encoder = gst.element_factory_make("flacenc", "encoder")
        self.sink = gst.element_factory_make("fdsink", "sink")

        self.level.set_property("message", True)

        self.recording_bin = gst.Bin()
        self.recording_bin.add(self.audiosrc, self.level, self.encoder, self.sink)
        gst.element_link_many (self.audiosrc, self.level, self.encoder, self.sink)        
        self._createUI()

        self.is_recording = False

    def _createUI(self):
        builder = gtk.Builder()
        builder.add_from_string(ui)
        builder.add_from_file(os.path.join(os.path.dirname(__file__), "audiosave.glade"))

        self.audiosave_dialog = builder.get_object("audiosave_dialog")
        self.audiosave_dialog.filename_entry = builder.get_object("filename")
        self.audiosave_dialog.folderchooser = builder.get_object("folderchooser")
        self.record_button = builder.get_object("record_button")
        self.button_image = builder.get_object("button_image")
        self.vumeter = FVUMeter() 

        self.pack_start(self.record_button, expand=False, fill=False)

        eventbox = gtk.EventBox()
        eventbox.add(self.vumeter)
        self.pack_start(eventbox, expand=True, fill=True)
        self.set_size_request(300, -1)

        self.record_button.set_sensitive(True)
        self.record_button.connect("clicked", self._recordCb)

    def _on_message(self, bus, message):
        if message.structure.get_name() == 'level':
            s = message.structure
            self.vumeter.freeze_notify()
            decay = clamp(s['decay'][0], -90.0, 0.0)
            peak = clamp(s['peak'][0], -90.0, 0.0)

            self.vumeter.set_property('decay', decay)
            self.vumeter.set_property('peak', peak)
        return True

    def _recordCb(self, widget):
        if not self.is_recording:
            self.start_recording()
            self.is_recording = True
            self.button_image.set_from_stock(gtk.STOCK_MEDIA_STOP, gtk.ICON_SIZE_LARGE_TOOLBAR)
        else:
            self.stop_recording()
            self.is_recording = False
            self.button_image.set_from_stock(gtk.STOCK_MEDIA_RECORD, gtk.ICON_SIZE_LARGE_TOOLBAR)

    def start_recording(self):
        self._tempfd, self._temppath = tempfile.mkstemp()
        self.sink.set_property("fd", self._tempfd)
        self._cb_id = self.app.current.pipeline.getBus().connect("message::element", self._on_message)
        self.app.current.pipeline.addBin(self.recording_bin) 
        self.app.current.pipeline.play()

    def stop_recording(self):
        self.app.current.pipeline.getBus().disconnect(self._cb_id)
        self.app.current.pipeline.stop()
        self.app.current.pipeline.removeBin(self.recording_bin)
        os.close(self._tempfd) # assuming gstreamer doesn't close the fd. Should check
        self._save_file()
       
    def _save_file(self):
        self.audiosave_dialog.set_transient_for(self.app.gui)
        response = self.audiosave_dialog.run()
        if response == gtk.RESPONSE_OK:
            self.file_path = os.path.join(self.audiosave_dialog.folderchooser.get_filename(),
                    self.audiosave_dialog.filename_entry.get_text())
            if os.path.exists(self.file_path):
                if self._sourceExists('file:///' + self.file_path):
                    iBox = gtk.MessageDialog(self.audiosave_dialog,
                            gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
                            "File already exists in the project and cannot be overwritten. Please choose a different filename")
                    iBox.run()
                    iBox.destroy()
                    self._save_file()
                    return
                mBox = gtk.MessageDialog(self.audiosave_dialog,
                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
                        "File already exists. Do you want to overwrite it?")
                mresponse = mBox.run()
                mBox.destroy()
                if mresponse == gtk.RESPONSE_NO:
                    self._save_file()
                    return
            shutil.copy(self._temppath, self.file_path)
            self.app.current.sources.connect("source-added", self._sourceAddedCb)
            self.app.current.sources.addUris(['file:///' + self.file_path])
        else:
            os.remove(self._temppath)

        self.audiosave_dialog.hide()
        self.audiosave_dialog.filename_entry.set_text("")

    def _sourceExists(self, uri):
        try:
            self.app.current.sources.getUri(uri)
            return True
        except:
            return False

    def _sourceAddedCb(self, unused, factory):
        # Add recorded file to timeline
        # TODO: Check to make sure that we're adding the correct factory
        timeline_obj = self.app.current.timeline.addSourceFactory(factory)
        self.app.current.sources.disconnect_by_func(self._sourceAddedCb)

    def show_all(self):
        HBox.show_all(self)
        self.vumeter.show()

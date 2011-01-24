import tempfile

import gst
import gtk

ui = """
 <interface>
  <requires lib="gtk+" version="2.16"/>
      <object class="GtkProgressBar" id="vumeter">
        <property name="visible">True</property>
        <property name="sensitive">False</property>
        <property name="show_text">True</property>
        <property name="text" translatable="yes">Microphone</property>
      </object>
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

class AudioRecorder(gtk.HBox):
    def __init__(self, instance):
        gtk.HBox.__init__(self)
        self.audiosrc = gst.element_factory_make("autoaudiosrc", "audiosrc")
        self.encoder = gst.element_factory_make("flacenc", "encoder")
        self.sink = gst.element_factory_make("fdsink", "sink")

        self.pipeline = gst.Pipeline()
        self.pipeline.add(self.audiosrc, self.encoder, self.sink)
        gst.element_link_many (self.audiosrc, self.encoder, self.sink)        

        self.app = instance
        self._createUI()

        self.is_recording = False

    def _createUI(self):
        builder = gtk.Builder()
        builder.add_from_string(ui)

        self.record_button = builder.get_object("record_button")
        self.button_image = builder.get_object("button_image")
        self.vumeter = builder.get_object("vumeter")

        self.pack_start(self.record_button, expand=False, fill=False)
        self.pack_start(self.vumeter, expand=True, fill=True)
        self.set_size_request(300, -1)

        self.record_button.set_sensitive(True)
        self.record_button.connect("clicked", self._recordCb)

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
        self.pipeline.set_state(gst.STATE_PLAYING)
        print "Recording to", self._temppath

    def stop_recording(self):
        self.pipeline.set_state(gst.STATE_NULL)

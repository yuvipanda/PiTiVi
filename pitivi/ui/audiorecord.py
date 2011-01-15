import gst

class AudioRecorder():
    def __init__(self):
        self.audiosrc = gst.element_factory_make("autoaudiosrc", "audiosrc")
        self.encoder = gst.element_factory_make("flacenc", "encoder")
        self.sink = gst.element_factory_make("filesink", "sink")

        self.pipeline = gst.Pipeline()
        self.pipeline.add(self.audiosrc, self.encoder, self.sink)
        gst.element_link_many (self.audiosrc, self.encoder, self.sink)        

    def start_recording(self, filepath):
        self.sink.set_property("location", filepath)
        self.pipeline.set_state(gst.STATE_PLAYING)

    def stop_recording(self):
        self.pipeline.set_state(gst.STATE_NULL)

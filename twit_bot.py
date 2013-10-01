class PostScheduler(threading.Thread):
  def __init__(self, api, simulate=False, controllers=None, default_time_to_sleep=60):
    threading.Thread.__init__(self)
    self.api = api
    self.controllers = controllers
    self.queue = Queue.Queue()
    self.post_objects = []
    self.default_time_to_sleep = default_time_to_sleep
    self.setDaemon(True)
    

class PostScheduler(threading.Thread):
    def __init__(self, api, simulate=False, controllers=None, default_time_to_sleep=60):
        threading.Thread.__init__(self)
        self.api = api
        self.controllers = controllers
        self.queue = Queue.Queue()
        self.post_objects = []
        self.default_time_to_sleep = default_time_to_sleep
        self.setDaemon(True)

    def run(self):
        while True:
            queue_object = self.queue.get()

            if self.queue.empty():
                self.queue.put(self.default_time_to_sleep)

            if isinstance(queue_object, (int, long, float)):
                time_to_sleep = queue_object
                if time_to_sleep > 0:
                    time.sleep(time_to_sleep)
                    self.evaluate_tweets()
            else:
                self.post_objects.append(queue_object)

            self.queue.task_done()

    def evaluate_tweets(self):
        self.count += 1
        seconds_from_midnight = (datetime.today() - datetime.min).seconds
        post_objects_to_remove = []

        for post_object in self.post_objects:
            can_be_handled = False
            for controller in self.controllers:
                if controller.can_handle_object(post_object):
                    can_be_handled = True
                    break
            if not can_be_handled:
                post_objects_to_remove.append(post_object)

        for post_object in post_objects_to_remove:
            self.post_objects.remove(post_object)

        for controller in self.controllers:
            chosen_object = None
            for post_object in self.post_objects:
                if self.evaluate_tweet(controller, post_object, seconds_from_midnight):
                    chosen_object = post_object
                    break
            if chosen_object != None:
                self.post_objects.remove(chosen_object)
                break
            self.evaluate_tweet(controller, { }, seconds_from_midnight)

            def evaluate_tweet(self, controller, post_object, seconds_from_midnight):
                probability = controller.probabilityToPost(post_object, seconds_from_midnight, self.default_time_to_sleep, self.simulate)
                if probability == 0:
                    return False
                steps = 10000.0
                random_number = random.randrange(steps)/steps
                if random_number <= probability:
                    self.posts += 1
                    print controller
                    print controller.composePost(self.api, post_object, self.simulate)
                    controller.postUpdateStatus(self.api, post_object)
                    return True
                return False

class PostController(object):
    def __init__(self, post_composers = [], postControllers = None, current_user=None):
        self.post_composers = post_composers
        self.current_user = current_user

    def can_handle_object(self, post_object):
        return len(post_object) == 0

    def probabilityToPost(self, post_object, seconds_from_midnight, time_step, simulate=False):
        if len(post_object) != 0:
            return 0
        if self.isCurrentUser(post_object):
            return 0
        # flat distribution 22 tweets per day
        one_day = 60.*60.*24./float(time_step)
        if simulate:
            one_day /= 60
        return 22./one_day

    def isCurrentUser(self, post_object):
        if self.current_user == None:
            print 'No current user skipping'
            return False
        # don't respond if the tweet belongs to the current user -- would be infinite loop!
        if post_object.has_key('user'):
            if post_object['user'].has_key('id_str'):
                return post_object['user']['id_str'] == self.current_user['id_str']
        return False

    def choosePostComposer(self):
        post_composers = []
        total_percent = 0
        for post_composer in self.post_composers:
            if post_composer.percent() == 100:
                return post_composer
            post_composers.append(post_composer)
            total_percent += post_composer.percent()
        probability = random.randrange(total_percent)
        threshold = 0
        for post_composer in post_composers:
            if threshold <= post_composer.percent():
                return post_composer
            threshold += post_composer.percent()
        return post_composer

    def composePost(self, api, post_object, simulate):
        return self.choosePostComposer().compose(api, post_object, simulate)

    class ReplyController(post.PostController):
    def __init__(self, post_composers = [], postControllers = None, current_user=None):
        post.PostController(post_composers, postControllers, current_user)
        self.post_composers = post_composers
        self.current_user = current_user
        self.reply_ids = { }

    def can_handle_object(self, post_object):
        if self.isCurrentUser(post_object):
            return False
        if not post_object.has_key('entities'):
            return False
        if not post_object['entities'].has_key('user_mentions'):
            return False
        for user_mention in post_object['entities']['user_mentions']:
            if user_mention['id_str'] == self.current_user['id_str']:
                return True
        return False

    def probabilityToPost(self, post_object, seconds_from_midnight, time_step, simulate=False):
        if self.isCurrentUser(post_object):
            return 0
        if not post_object.has_key('entities'):
            return 0
        if not post_object['entities'].has_key('user_mentions'):
            return 0
        for user_mention in post_object['entities']['user_mentions']:
            if user_mention['id_str'] == self.current_user['id_str']:
                return self.probabilityForId(post_object, seconds_from_midnight, time_step)
        return 0

    def probabilityForId(self, post_object, seconds_from_midnight, time_step):
        if not post_object.has_key('user'):
            return 0
        if not post_object['user'].has_key('id_str'):
            return 0
        user_id = post_object['user']['id_str']
        if not self.reply_ids.has_key(user_id):
            self.reply_ids[user_id] = { 'probability' : 1, 'first_reply' : datetime.today(), 'last_attempt' : datetime.min }

        current_datetime = datetime.today()
        if (current_datetime - self.reply_ids[user_id]['first_reply']).seconds > 1:#60*60*24:
            self.reply_ids[user_id] = { 'probability' : 1, 'first_reply' : datetime.today(), 'last_attempt' : datetime.min }
            return 1

        probability = self.reply_ids[user_id]['probability']
        delta = (datetime.today() - self.reply_ids[user_id]['last_attempt'])
        if delta.microseconds < 500:
            probability = 0

        self.reply_ids[user_id]['last_attempt'] = datetime.today()

        return probability

    def postUpdateStatus(self, api, post_object):
        user_id = post_object['user']['id_str']
        probability = float(self.reply_ids[user_id]['probability'])
        self.reply_ids[user_id]['probability'] = probability * 0.5

        class FortuneComposer(PostComposer):
    def __init__(self):
        self.fortunes = open('fortunes').read().split('\n%\n')
        for fortune in self.fortunes:
            if len(fortune) > 140:
                self.fortunes.remove(fortune)

    def compose(self, api, post_object, simulate):
        fortune = None
        screen_name = None
        if post_object.has_key('user'):
            if post_object['user'].has_key('screen_name'):
                screen_name = post_object['user']['screen_name']
        if screen_name != None:
            fortune = self.chooseFortune(140, screen_name)
        else:
            fortune = self.chooseFortune()
        if fortune == None:
            return None
        if simulate:
            return fortune
        if post_object.has_key('id_str') and screen_name != None:
            return api.updateStatus(status=fortune, in_reply_to_status_id=post_object['id_str'])
        else:
            return api.updateStatus(status=fortune)

    def chooseFortune(self, max_len=140, screen_name=None):
        fortune = ''
        if screen_name != None:
            fortune += '@' + screen_name + ' '
            max_len -= len(fortune)
        tmp_fortune = random.choice(self.fortunes)
        count = 0
        while len(tmp_fortune) > max_len:
            if count > 1000:
                return None
            tmp_fortune = random.choice(self.fortunes)
            count += 1
        fortune += tmp_fortune
        return fortune

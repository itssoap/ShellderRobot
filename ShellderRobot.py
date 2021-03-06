#/usr/bin/python3

import os, time, json, platform, importlib, subprocess,  telepot 
from subprocess import TimeoutExpired
from telepot.loop import MessageLoop


class TelegramShellBot:
    _token = ''
    _bot = None
    _adm_chat_id = 0
    _cmdList = []
    _config_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)),'ShellderRobot.conf')
    _plugins = []
    _encoding = 'utf8'

    def loadplugins(self):
        path = os.path.abspath(__file__)
        path = os.path.join(os.path.dirname(path),'plugins')
        for filename in os.listdir(path):
            name, ext = os.path.splitext(filename)
            if ext == '.py':
                try:
                    p = importlib.import_module('plugins.'+name)
                    p.plugin_init(self)
                    self._plugins.append(p)
                except Exception as e:
                    print ("Error loading plugin {0}: {1}".format(filename, e))

    def saveconfig(self):
        c = {}
        c['token'] = self._token
        c['chat_id'] = self._adm_chat_id
        with open(self._config_filename, 'w') as outfile:
            json.dump(c, outfile)

    def loadconfig(self):
        try:
            with open(self._config_filename) as json_data_file:
                c = json.load(json_data_file)
                self._token = c['token']
                self._adm_chat_id = c['chat_id']
                return True
        except Exception:
            pass
        return False

    def setup(self):
        print('Input bot token:', end='')
        self._token = input()
        self._bot = telepot.Bot(self._token)
        p = self._bot.getMe()
        print('Bot: ', p['username'])
        print('Waiting for admin connect (Ctrl+c for break)...')
        p = []
        offset = None 
        while True:
            p = self._bot.getUpdates(offset=offset)
            # print(p)
            for m in p:
                if 'update_id' in m.keys():
                    offset = m['update_id']+1
                print('User "', m['message']['chat']['username'], '" is bot admin?(Y/n)', end='')
                s = input()
                if s in ['', 'y', 'Y']:
                    self._adm_chat_id = m['message']['chat']['id']
                    return True
            time.sleep(1)
        return False

    def find_plugincmd(self, txt):
        for p in self._plugins:
            try:
                if p.plugin_ismycmd(txt):
                    return p
            except:
                pass
        return None

    def handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        # print(content_type, chat_type, chat_id)
        # print(msg)
        try:
            if self._adm_chat_id == chat_id:
                self.handle_master(msg)
            else:
                self.sendMessage("Non admin message: {0} from {1}".format(msg, chat_id))
        except Exception as err:
            self.sendMessage("error: {0}".format(err))

    def handle_master(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text':
            t = msg['text']
            s = t.split(' ')
            if len(s) > 0 and s[0].lower() == 'cd':
                if len(s) > 1:
                    os.chdir(" ".join(s[1:]).replace("\"", ""))
                self.sendMessage(os.getcwd())
            else:
                if not self.cmdHandler(t):        
                    self.call_shell(t)
        elif content_type == 'document':
            doc = msg['document']
            f = os.path.join(os.getcwd(), doc['file_name'])
            self._bot.download_file(doc['file_id'], f)
            self.sendMessage(f)        

    def cmdHandler(self, txt):
        cmd = txt.split(' ')
        c = cmd[0].lower()
        if c == '/start':
            self.sendMessage('Hi master!')
        # elif c == '/ping':
        #     self.sendMessage('pong')
        # elif c == '/get':
        #     self.sendMessage('Not supported. yet')
        #     f = txt[4:].strip()
        #     bot.sendDocument()
        else:
            plug = self.find_plugincmd(txt)
            if plug:
                plug.plugin_handler(txt, self)
                return True
            else:
                return False

    def call_shell(self, text):
        t = text
        p = subprocess.Popen(t, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        out = None
        try:
            out, err = p.communicate(timeout=60)
        except TimeoutExpired:
            p.terminate()
            try:
                out, err = p.communicate(timeout=3)
            except TimeoutExpired:
                pass
            self.sendMessage("timeout")
        if out:
            while len(out) > 4000:
                o2, out = out[:4000], out[4000:]
                self.sendMessage(o2.decode(self._encoding))                            
            if out:
                self.sendMessage(out.decode(self._encoding))
        elif p.returncode:
            self.sendMessage("exit code " + str(p.returncode))
        else:
            self.sendMessage("none")

    def sendMessage(self, msg):
        self._bot.sendMessage(self._adm_chat_id, msg)

    def __init__(self):
        if platform.system() == 'Windows':
            self._encoding = 'cp1251'
        if not self.loadconfig():
            if not self.setup():
                print('Wrong setup')
                exit()
            else:
                self.saveconfig()
        self._bot = telepot.Bot(self._token)
        self.loadplugins()
        MessageLoop(self._bot, self.handle).run_as_thread()
        print('Listening ...')
        # Keep the program running.
        while 1:
            time.sleep(10)

if __name__ == '__main__':
    print('ShellderRobot by AnimeKaizoku')
    TelegramShellBot()

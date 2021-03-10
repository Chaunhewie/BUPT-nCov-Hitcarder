# -*- coding: utf-8 -*-
# /usr/bin/python
import os
import requests, json, re
import time, datetime
from apscheduler.schedulers.blocking import BlockingScheduler


class DaKa(object):
    def __init__(self, username, password, sms_number="", sms_api_key=""):
        self.username = username
        self.password = password
        self.sms_number = sms_number
        self.sms_api_key = sms_api_key
        self.info = None

        self.login_url = "https://app.bupt.edu.cn/uc/wap/login?redirect=https%3A%2F%2Fapp.bupt.edu.cn%2Fncov%2Fwap%2Fdefault%2Findex"
        self.base_url = "https://app.bupt.edu.cn/ncov/wap/default/index"
        self.save_url = "https://app.bupt.edu.cn/ncov/wap/default/save"
        self.login_check_url = "https://app.bupt.edu.cn/uc/wap/login/check"
        self.sess = requests.Session()

        # self.sms_url_api = "https://api.binstd.com/sms/send?mobile={}&content={}&appkey={}"
        self.sms_url_api = 'https://sc.ftqq.com/{}.send?text={}&desp={}'

    def login(self):
        """Login to BUPT platform"""
        res = self.sess.get(self.login_url)
        
        if res.status_code != 200:
            raise Exception("{} 登陆平台失败，失败代码{}".format(self.username,res.status_code))

        data = {
            'username': self.username,
            'password': self.password,
        }
        res = self.sess.post(url=self.login_check_url, data=data)
        ret = json.loads(res.content.decode())

        if ret['e'] != 0:
            raise Exception("{} 登陆失败，原因{}".format(self.username,ret['m']))
        return ret
    
    def post(self):
        """Post the hitcard info"""
        res = self.sess.post(self.save_url, data=self.info)
        if res.status_code != 200:
            raise Exception("{} post info faild, statu code = {}".format(self.username, res.status_code))
        return json.loads(res.text)

    @ staticmethod
    def get_date():
        today = datetime.date.today()
        return "%4d%02d%02d" % (today.year, today.month, today.day)
        
    def get_info(self, html=None):
        """Get hitcard info, which is the old info with updated new time."""
        if not html:
            res = self.sess.get(self.base_url)
            if res.status_code != 200:
                raise Exception("{} get info faild, statu code = {}".format(self.username, res.status_code))
            html = res.content.decode()
        old_info = json.loads(re.findall(r'oldInfo: (.*)', html)[0][:-1])
        print("old_info:", old_info)
        name = re.findall(r'realname: "([^\"]+)",', html)[0]
        number = re.findall(r"number: '([^\']+)',", html)[0]

        new_info = old_info.copy()
        new_info['name'] = name
        new_info['number'] = number
        new_info["date"] = self.get_date()
        new_info["created"] = round(time.time())

        self.info = new_info

        self.save_info()

        return new_info

    @ staticmethod
    def _rsa_encrypt(self, password_str, e_str, m_str):
        password_bytes = bytes(password_str, 'ascii') 
        password_int = int.from_bytes(password_bytes, 'big')
        e_int = int(e_str, 16) 
        m_int = int(m_str, 16)
        result_int = pow(password_int, e_int, m_int)
        return hex(result_int)[2:].rjust(128, '0')

    def save_info(self):
        with open("cache_info_bk.json", "w", encoding="utf-8") as file:
            json.dump(self.info, file)

    def send_sms(self, res):
        print("-----------sms----------")
        if len(self.sms_api_key) <= 0 or len(self.sms_number) <= 0:
            return "没有配置短信接收手机号码或者短信api_key"
        if res['e'] == 0:
            msg = "打卡成功！\n{}".format(res["m"])
        else:
            msg = "打卡失败！\n{}".format(res["m"])
        print(msg)
        url = self.sms_url_api.format(self.sms_api_key, "BUPT-nCov-Hitcarder Check in", msg)
        print(url)
        res = json.loads(requests.get(url).content)
        print(res)
        return res

    def daka(self):
        ret = []
        res = self.login()
        ret.append(res)
        print("--------login res-------\n----", res)
        res = self.get_info()
        ret.append(res)
        print("--------get_info res-------\n----", res)
        res = self.post()
        ret.append(res)
        print("--------post res-------\n----", res)
        res = self.send_sms(res)
        ret.append(res)
        print("--------send_sms res-------\n----", res)
        return ret


def main(username, password, sms_number="", sms_api_key=""):

    dk = DaKa(username, password, sms_number, sms_api_key)
    try:
        dk.daka()
    except Exception as e:
        print(e)
    finally:
        return 0


def run():
    if not os.path.exists('./config.json'):
        msg = '''{
    "sms_api_key": "Server酱的SCKEY",
    "info": [
        {
            "username": "你的北邮统一认证平台用户名",
            "password": "你的北邮统一认证平台密码",
            "schedule": {
                "on": false,
                "hour": "0",
                "minute": "1"
            }
        },
        {
            "username": "你的北邮统一认证平台用户名",
            "password": "你的北邮统一认证平台密码",
            "schedule": {
                "on": false,
                "hour": "0",
                "minute": "2"
            }
        }
    ]
}
'''
        print("请创建config.json文件到项目路径({})下，内容如下：".format(os.getcwd(), msg))
        return

    configs = json.loads(open('./config.json', 'r', encoding="utf-8").read())
    sms_api_key = configs.get("sms_api_key", "")
    for config in configs["info"]:
        username = config["username"]
        password = config["password"]
        sms_number = config.get("sms_number", "")
        scheduler_flag = config["schedule"]["on"]
        hour = config["schedule"]["hour"]
        minute = config["schedule"]["minute"]

        if scheduler_flag:
            # Schedule task
            scheduler = BlockingScheduler()
            scheduler.add_job(main, 'cron', args=[username, password], hour=hour, minute=minute)
            print('⏰ 已启动定时程序，每天 %02d:%02d 为您打卡' % (int(hour), int(minute)))
            print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

            try:
                scheduler.start()
            except (KeyboardInterrupt, SystemExit):
                pass
        else:
            main(username, password, sms_number, sms_api_key)


if __name__ == "__main__":
    run()

import requests
import json

access_token='0ade599901a68fe52c268fcb3172513714e26ef8bbd11db70ba1d78a5afea1ec'
coin_reminder_chat=f'https://oapi.dingtalk.com/robot/send?access_token={access_token}'

def sent_msg(msg):
    data_json = {
        "msgtype":"text",
        "text": {"content": msg}
    }
    headers = {
        'content-type': 'application/json'
    }

    resp = requests.post(coin_reminder_chat, json=data_json, headers=headers)
    return 0


if __name__ == '__main__':
    sent_msg('财富密码：测试2')
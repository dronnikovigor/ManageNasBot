# Manage NAS Telegram Bot

[![Python Version](https://www.python.org/downloads/release/python-3110/)](https://img.shields.io/badge/python-3.8_%7C_3.9_%7C_3.10_%7C_3.11-blue)

Tool for remote managing of NAS via Telegram Bot.

## Features:

- Reboot / Shutdown system
- Manage Docker containers: stop, restart, logs tail
- Manage **Fail2ban**: start, stop, status of system service, ban / unban IP, logs tail
- Download files

## Table of Contents

* [Installation](#installation)
* [Usage](#usage)
  * [Configuration](#configuration)
  * [Telegram](#telegram)
  * [Files](#files)
* [Contributing](#contributing)

## Installation

1. Install Python 3.8+.   
2. Clone project. For e.g. to `/usr/local/bin/ManageNasBot`
3. Navigate to cloned project.  
4. Install dependencies:

```commandline
pip install -r requirements.txt
```
5. Register new bot in @BotFather, put API key into `./config.ini`, field `bot_token`.  
**NB**: don't make your bot public.
6. Start conversation with bot, send any message.  
7. Replace `REPLACETOKENHERE` with your API key from step 3 and execute:
```commandline
curl https://api.telegram.org/botREPLACETOKENHERE/getUpdates
```
8. You will get JSON with your messages. Find your Telegram Account ID: message -> from -> id. 
Put in into `./config.ini`, field `owner_id`.
9. You can make bot start within system startup. 
Execute:   
`sudo nano /etc/systemd/system/manage-nas-bot.service`  
**NB**: if you want just to start bot, you can launch it as usual python program:  
`python ./main.py`  
10. Insert:
```
[Unit]
Description=Manage Nas Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/bin/ManageNasBot
ExecStart=/usr/bin/python3 main.py

[Install]
WantedBy=multi-user.target
```
11. Execute:  
`sudo systemctl daemon-reload`
12. Execute:  
`sudo systemctl enable manage-nas-bot`

<br>
Check status after of service:  
`sudo systemctl status telegram-bot`
  
Logs are located at `./logs`

## Usage

### Configuration
#### Telegram
Telegram API key and your profile ID are configured in `./config.ini`. Steps 5-8 in installation instruction.
#### Files
Files to show in Fail2ban section or in Files section can be configured in `./mapping.json`.  
* `fail2ban_logs` - files to be shown in Fail2ban section. Tail of file is show - not more than 15 lines (4000 symbols max).  
* `files_to_download` - files to be sent in chat in Files section.  
Example:  
```json lines
{
  "fail2ban_logs": {
    "fail2ban": "/var/log/fail2ban.log",
    "nextcloud log": "/path/to/nextcloud/nextcloud-log.log",
    "nginx log": "/path/to/nginx/proxy-1-access.log"
  },
  "files_to_download": {
    "fail2ban log": "/var/log/fail2ban.log"
  }
}

```
### Fail2ban
It will automatically grab all your active jails to show in ban / unban IP section.  

## Contributing

Bug reports and pull requests are welcome on GitHub at https://github.com/dronnikovigor/ManageNasBot
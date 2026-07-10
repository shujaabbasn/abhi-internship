from crontab import CronTab
import os

backend_dir=os.path.dirname(os.path.abspath(__file__))
command="cd "+backend_dir+" && /usr/bin/python3 refresh_intents_cache.py >> /tmp/refresh_intents_cache.log 2>&1"

cron=CronTab(user=True)

existing=list(cron.find_comment("intents-sync"))
for job in existing:
    cron.remove(job)

job=cron.new(command=command,comment="intents-sync")
job.minute.every(2)

cron.write()

print("Cron job installed:")
print(job)
from crontab import CronTab
import os

cron_script=os.path.join(os.path.dirname(os.path.abspath(__file__)),"cron.py")
command="/usr/bin/python3 "+cron_script
cron=CronTab(user=True)

existing=list(cron.find_comment("sync"))
for job in existing:
    cron.remove(job)

job=cron.new(command=command,comment="sync")
job.minute.every(1)
cron.write()

print("Cron job installed:")
print(job)
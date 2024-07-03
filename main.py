import os
import json
from icalendar import Calendar, Event, Alarm, vText, Timezone, TimezoneStandard
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_event(data, calendar):
    for item in data['Result'][0]['DisplayData']['resultData']['tplData']['data']['almanac']:
        try:
            timestamp = int(item['timestamp'])
            event_date = datetime.fromtimestamp(timestamp)
            nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"
            summary = ','.join([f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else item.get('festivalList', '日历事件')
            description = f"【{nongli}】\n🎉 {summary}\n✅宜：{item['suit']}\n❌忌：{item['avoid']}"

            event = Event()
            event.add('summary', f"★黄历★:{nongli}")
            event.add('dtstart', event_date.date())
            event.add('dtend', (event_date + timedelta(days=1)).date())
            event.add('dtstamp', datetime.now())
            event.add('uid', f"{event_date.strftime('%Y%m%d')}_jr")
            event.add('created', datetime.now())
            event.add('description', vText(description))
            event.add('last-modified', datetime.now())
            event.add('sequence', 0)
            event.add('status', 'CONFIRMED')
            event.add('transp', 'TRANSPARENT')

            # 添加提醒事件
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', 'Event Reminder')
            alarm_time = event_date.replace(hour=8, minute=30, second=0, microsecond=0)
            trigger_time = timedelta(hours=8, minutes=30)
            alarm.add('trigger', trigger_time)
            event.add_component(alarm)

            calendar.add_component(event)
        except (ValueError, KeyError) as e:
            logging.error(f"Error processing item: {item}, error: {e}")

def generate_ical_for_year(base_path, year, final_calendar):
    year_path = os.path.join(base_path, str(year))
    if not os.path.exists(year_path):
        logging.warning(f"路径 {year_path} 不存在，跳过该年份。")
        return

    for file_name in os.listdir(year_path):
        if file_name.endswith('.json'):
            file_path = os.path.join(year_path, file_name)
            logging.info(f"正在处理文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    create_event(data, final_calendar)
                except json.JSONDecodeError:
                    logging.error(f"Error decoding JSON from file: {file_path}")
                except KeyError:
                    logging.error(f"Key error in file: {file_path}")

def create_final_ical(base_path):
    final_calendar = Calendar()
    final_calendar.add('VERSION', '2.0')
    final_calendar.add('PRODID', '-//My Calendar Product//mxm.dk//')
    final_calendar.add('METHOD', 'PUBLISH')
    final_calendar.add('X-WR-CALNAME', '节假日和黄历')
    final_calendar.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    final_calendar.add('X-WR-CALDESC', f'中国以及国际节假日，备注有黄历，更新日期:{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    # 设置时区信息
    timezone = Timezone()
    timezone.add('TZID', 'Asia/Shanghai')
    timezone.add('X-LIC-LOCATION', 'Asia/Shanghai')
    standard = TimezoneStandard()
    standard.add('TZOFFSETFROM', timedelta(hours=8))
    standard.add('TZOFFSETTO', timedelta(hours=8))
    standard.add('TZNAME', 'CST')
    standard.add('DTSTART', datetime(1970, 1, 1, 0, 0, 0))
    timezone.add_component(standard)
    final_calendar.add_component(timezone)

    years = list(range(2022, 2031))
    for year in years:
        generate_ical_for_year(base_path, year, final_calendar)

    output_file = os.path.join(base_path, 'holidays_calendar_2022-2030.ics')
    with open(output_file, 'wb') as f:
        f.write(final_calendar.to_ical())
    logging.info(f"最终的iCalendar文件已成功生成：{output_file}")

def main():
    base_path = './openApiData/calendar_new'
    create_final_ical(base_path)

if __name__ == "__main__":
    main()

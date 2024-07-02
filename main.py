#!./usr/bin/env.python
# .-*- coding: utf-8 -*-
# ._author_.=."Max丶"
# ._Email:_.=."max@chamd5.org"
import os
import json
from icalendar import Calendar, Event, vText
from datetime import datetime, timedelta


def create_event(data, calendar):
    for item in data['Result'][0]['DisplayData']['resultData']['tplData']['data']['almanac']:
        try:
            timestamp = int(item['timestamp'])
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')
            nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"
            summary = ','.join(
                [f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else item.get(
                'festivalList', '日历事件')
            description = f"【{nongli}】\n🎉 {summary}\n✅宜：{item['suit']}\n❌忌：{item['avoid']}"

            event = Event()
            event.add('summary', f"★黄历★:{nongli}")
            event.add('dtstart', datetime.fromtimestamp(timestamp).date())
            event.add('dtend', datetime.fromtimestamp(timestamp).date() + timedelta(days=1))
            event.add('dtstamp', datetime.fromtimestamp(timestamp))
            event.add('uid', f"{date_str}_jr@zqzess")
            event.add('created', datetime.now())
            event.add('description', vText(description))
            event.add('last-modified', datetime.now())
            event.add('sequence', 0)
            event.add('status', 'CONFIRMED')
            event.add('transp', 'TRANSPARENT')

            calendar.add_component(event)
        except (ValueError, KeyError) as e:
            print(f"Error processing item: {item}, error: {e}")


def generate_ical_for_year(base_path, year, final_calendar):
    year_path = os.path.join(base_path, str(year))
    if not os.path.exists(year_path):
        print(f"路径 {year_path} 不存在，跳过该年份。")
        return

    for file_name in os.listdir(year_path):
        if file_name.endswith('.json'):
            file_path = os.path.join(year_path, file_name)
            print(f"正在处理文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    create_event(data, final_calendar)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from file: {file_path}")
                except KeyError:
                    print(f"Key error in file: {file_path}")


def create_final_ical(base_path):
    final_calendar = Calendar()

    # 添加 VCALENDAR 头部信息
    final_calendar.add('BEGIN', 'VCALENDAR')
    final_calendar.add('VERSION', '2.0')
    final_calendar.add('PRODID', '-//My Calendar Product//mxm.dk//')
    final_calendar.add('METHOD', 'PUBLISH')
    final_calendar.add('X-WR-CALNAME', '节假日和黄历')
    final_calendar.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    final_calendar.add('X-WR-CALDESC',
                       f'中国以及国际节假日，备注有黄历，更新日期:{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    # 添加 VTIMEZONE 信息
    final_calendar.add('BEGIN', 'VTIMEZONE')
    final_calendar.add('TZID', 'Asia/Shanghai')
    final_calendar.add('X-LIC-LOCATION', 'Asia/Shanghai')
    final_calendar.add('BEGIN', 'STANDARD')
    final_calendar.add('TZOFFSETFROM', timedelta(hours=8))
    final_calendar.add('TZOFFSETTO', timedelta(hours=8))
    final_calendar.add('TZNAME', 'CST')
    final_calendar.add('DTSTART', datetime(1970, 1, 1, 0, 0, 0))
    final_calendar.add('END', 'STANDARD')
    final_calendar.add('END', 'VTIMEZONE')

    # 生成 2022 到 2030 年的 iCalendar 数据
    years = range(2022, 2031)
    for year in years:
        generate_ical_for_year(base_path, year, final_calendar)

    # 写入最终的 iCalendar 文件
    output_file = os.path.join(base_path, './holidays_calendar_2022-2030.ics')
    with open(output_file, 'wb') as f:
        f.write(final_calendar.to_ical())
    print(f"最终的 iCalendar 文件已成功生成：{output_file}")


def main():
    base_path = './openApiData/calendar_new'
    create_final_ical(base_path)


if __name__ == "__main__":
    main()

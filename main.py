import os
import json
import re
from icalendar import Calendar, Event, vText, vDatetime, Timezone, TimezoneStandard
from datetime import datetime, timedelta
import logging

# 设置日志记录格式和级别
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载干支数据
def load_ganzhi_data(file_path):
    """加载本地干支数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)  # 加载 JSON 数据
    except FileNotFoundError:
        logging.error(f"未找到干支数据文件：{file_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"解析干支 JSON 文件出错：{file_path}")
        return {}

# 从干支数据中提取指定日期的干支信息
def get_ganzhi_info(ganzhi_data, date):
    """从干支数据中获取指定日期的干支信息"""
    return ganzhi_data.get(date, "未知干支")  # 如果日期不存在，返回默认值

# 加载节庆数据
def load_festival_data(file_path):
    """加载本地节庆数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['日期']: item['节庆'] for item in data.get('祭祀日程', [])}
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
        return {}

# 清理描述中的无效数据或特殊字符
def clean_description(text):
    """清理节庆名称或描述中的无效字符"""
    text = text.replace("\\,", ",")  # 移除不必要的转义字符
    text = re.sub(r',六九', '', text)  # 删除所有 "六九" 字符
    return text.strip()  # 去除首尾空格

# 创建日历事件
def create_event(item, calendar, festival_data, ganzhi_data):
    try:
        timestamp = int(item['timestamp'])
        event_date = datetime.fromtimestamp(timestamp)
        nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"
        event_date_str = event_date.strftime("%Y-%m-%d")  # 格式化日期为字符串

        # 获取干支信息
        ganzhi_info = get_ganzhi_info(ganzhi_data, event_date_str)

        # 获取节庆名称和描述
        festival_name = ','.join([f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else ''
        festival_name = clean_description(festival_name)
        festival_description = festival_data.get(nongli, '无节庆信息')

        # 构建事件描述
        description = f"📅 **农历**: {nongli}\n🌀 **干支**: {ganzhi_info}\n"
        if festival_name:
            description += f"🎉 **节庆**: {festival_name}\n"
        description += f"✅ **宜**: {item['suit']}\n❌ **忌**: {item['avoid']}\n"

        # 创建事件对象
        event = Event()
        event.add('SUMMARY', f"★黄历★: {nongli}")
        event.add('DESCRIPTION', vText(description))
        event.add('DTSTART', vDatetime(event_date))
        event.add('DTEND', vDatetime(event_date + timedelta(days=1)))
        event.add('UID', f"{event_date.strftime('%Y%m%d')}@calendar")
        event.add('DTSTAMP', vDatetime(datetime.utcnow()))

        calendar.add_component(event)
        logging.debug(f"Added event: {event}")
    except Exception as e:
        logging.error(f"Error processing item: {item}, error: {e}")

# 创建最终的 iCalendar 文件
def create_final_ical(base_path, festival_data, ganzhi_data):
    final_calendar = Calendar()
    final_calendar.add('VERSION', '2.0')
    final_calendar.add('PRODID', '-//My Calendar Product//mxm.dk//')
    final_calendar.add('METHOD', 'PUBLISH')
    final_calendar.add('X-WR-CALNAME', '节假日和黄历')
    final_calendar.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    final_calendar.add('X-WR-CALDESC', '中国黄历及节假日')

    years = list(range(2025, 2031))
    for year in years:
        year_path = os.path.join(base_path, str(year))
        if not os.path.exists(year_path):
            logging.warning(f"路径 {year_path} 不存在，跳过该年份。")
            continue

        for file_name in os.listdir(year_path):
            if file_name.endswith('.json'):
                file_path = os.path.join(year_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        for item in data.get('Result', [])[0].get('DisplayData', {}).get('resultData', {}).get('tplData', {}).get('data', {}).get('almanac', []):
                            create_event(item, final_calendar, festival_data, ganzhi_data)
                    except Exception as e:
                        logging.error(f"Error processing file: {file_path}, error: {e}")

    # 输出 iCalendar 文件
    output_file = os.path.join(base_path, 'holidays_calendar.ics')
    with open(output_file, 'wb') as f:
        f.write(final_calendar.to_ical())
    logging.info(f"iCalendar 文件已生成: {output_file}")

# 主函数
def main():
    base_path = './openApiData/calendar_new'
    festival_data = load_festival_data('./shenxian.json')  # 节庆数据
    ganzhi_data = load_ganzhi_data('./ganzhi_data.json')  # 干支数据
    create_final_ical(base_path, festival_data, ganzhi_data)

if __name__ == "__main__":
    main()
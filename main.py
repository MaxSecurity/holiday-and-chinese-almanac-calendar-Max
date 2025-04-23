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

# 加载节气数据
def load_jieqi_data(file_path):
    """加载本地节气数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['节气']: item['节庆'] for item in data.get('祭祀日程', [])}
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
def create_event(item, calendar, festival_data, jieqi_data, deity_data, ganzhi_data):
    try:
        timestamp = int(item['timestamp'])
        event_date = datetime.fromtimestamp(timestamp)
        nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"
        event_date_str = event_date.strftime("%Y-%m-%d")  # 格式化日期为字符串

        # 获取干支信息
        ganzhi_info = get_ganzhi_info(ganzhi_data, event_date_str)

        # 获取节庆名称
        festival_name = ','.join([f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else item.get('festivalList', '')
        festival_name = clean_description(festival_name)

        # 获取节庆详细信息
        festival_details = festival_data.get(nongli, '')
        festival_details = clean_description(festival_details)

        # 构建描述信息
        description = []
        if festival_name:
            description.append(f"🎉 **节庆**: {festival_name}")
        description.append(f"📅 **农历**: {nongli}")
        description.append(f"🌀 **干支**: {ganzhi_info}")
        if festival_details:
            description.append(f"🌟 **神仙**: {festival_details}")
        description.append(f"✅ **宜**: {item['suit']}")
        description.append(f"❌ **忌**: {item['avoid']}")

        # 创建事件对象
        event = Event()
        event.add('summary', vText(f"★黄历★:{nongli}"))
        event.add('dtstart', vDatetime(event_date.replace(hour=8, minute=30, second=0, microsecond=0)))
        event.add('dtend', vDatetime(event_date.replace(hour=9, minute=30, second=0, microsecond=0)))
        event.add('description', vText("\n".join(description)))  # 合并描述为字符串
        event.add('uid', f"{event_date.strftime('%Y%m%d')}_jr")
        event.add('last-modified', vDatetime(datetime.now()))
        event.add('sequence', 0)

        # 添加事件到日历中
        calendar.add_component(event)
        logging.debug(f"Added event: {event}")
    except Exception as e:
        logging.error(f"Error processing item: {item}, error: {e}")

# 创建最终的 iCalendar 文件
def create_final_ical(base_path, festival_data, jieqi_data, deity_data, ganzhi_data):
    final_calendar = Calendar()
    final_calendar.add('VERSION', '2.0')
    final_calendar.add('PRODID', '-//My Calendar Product//mxm.dk//')
    final_calendar.add('METHOD', 'PUBLISH')
    final_calendar.add('X-WR-CALNAME', '节假日和黄历')
    final_calendar.add('X-WR-CALDESC', f'包含节假日、黄历和干支信息的日历文件')
    final_calendar.add('X-WR-TIMEZONE', 'Asia/Shanghai')

    # 添加时区信息
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

    # 遍历年份生成事件
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
                        for item in data['Result'][0]['DisplayData']['resultData']['tplData']['data']['almanac']:
                            create_event(item, final_calendar, festival_data, jieqi_data, deity_data, ganzhi_data)
                    except Exception as e:
                        logging.error(f"Error processing file {file_path}: {e}")

    # 写入最终的 iCalendar 文件
    output_file = os.path.join(base_path, 'holidays_calendar.ics')
    with open(output_file, 'wb') as f:
        f.write(final_calendar.to_ical())
    logging.info(f"iCalendar文件已生成：{output_file}")

# 主函数入口
def main():
    base_path = './openApiData/calendar_new'
    festival_data = load_festival_data('./shenxian.json')
    jieqi_data = load_jieqi_data('./jieqi.json')
    deity_data = load_festival_data('./deity.json')
    ganzhi_data = load_ganzhi_data('./ganzhi_data.json')  # 加载干支数据
    create_final_ical(base_path, festival_data, jieqi_data, deity_data, ganzhi_data)

if __name__ == "__main__":
    main()
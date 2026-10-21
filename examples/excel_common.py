import zipfile
import xml.etree.ElementTree as ET

def disk_rows(path):
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(n.text or '' for n in x.findall('.//s:t', ns)) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        rows = []
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('s:sheetData/s:row', ns):
            values = []
            for cell in row.findall('s:c', ns):
                kind = cell.get('t'); node = cell.find('s:v', ns)
                if kind == 'inlineStr': value = ''.join(n.text or '' for n in cell.findall('.//s:t', ns))
                elif kind == 's': value = shared[int(node.text)]
                elif node is None: value = None
                elif kind in (None, 'n'): value = float(node.text)
                else: value = node.text
                values.append(value)
            rows.append(values)
        return rows


def excel_blocks(output):
    v=lambda n:{'variable':n}
    return [
        {'prototype':'programing.variable','label':'构造输出表','inputs':{'value_type':'list','value':{'expression':'[]'}},'output':'export_rows'},
        {'prototype':'excel.launch','label':'新建结果工作簿','inputs':{'launch_way':'create','driver_way':'openpyxl','save_filename':str(output),'isvisible':False},'output':'excel_instance'},
        {'prototype':'excel.write_data_to_workbook','label':'写入结果','inputs':{'workbook':v('excel_instance'),'write_range':'area','row_num':1,'column_name':'A','content':v('export_rows'),'sheet_name':'Sheet'}},
        {'prototype':'excel.read_data_from_workbook','label':'读取结果核对','inputs':{'workbook':v('excel_instance'),'read_way':'used_range','sheet_name':'Sheet','has_header_row':False},'output':'verified_rows'},
        {'prototype':'excel.save','label':'保存并关闭','inputs':{'excel_instance':v('excel_instance'),'save_way':'save','is_close_after_save':True}}
    ]

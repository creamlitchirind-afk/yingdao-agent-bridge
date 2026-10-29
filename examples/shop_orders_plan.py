"""Native-only recipe for the inspected Yingdao learning shop."""
import json
from pathlib import Path

URL='https://shop.yingdao.com/list/table-list'
HEADERS=['订单编号','商品名称','金额','日期','状态']
def remap_variables(plan,mapping):
    def visit(value):
        if isinstance(value,list):return [visit(x) for x in value]
        if isinstance(value,dict):
            if set(value)=={'variable'}:return {'variable':mapping.get(value['variable'],value['variable'])}
            return {k:visit(v) for k,v in value.items()}
        return value
    result=visit(plan)
    for block in result['blocks']:
        if 'output' in block:block['output']=mapping.get(block['output'],block['output'])
        if 'outputs' in block:block['outputs']={k:mapping.get(v,v) for k,v in block['outputs'].items()}
    return result

def make_plan(product,pages,output,raw_output):
    blocks=[]
    v=lambda n:{'variable':n}
    def add(p,i=None,o=None,outputs=None):
        b={'prototype':p,'label':p,'inputs':i or {}}
        if o:b['output']=o
        if outputs:b['outputs']=outputs
        blocks.append(b)
    def log(s):add('programing.log',{'type':'info','text':s})
    def j(data,o):add('json.to_json',{'text':json.dumps(data,ensure_ascii=False)},o)
    def elem(lst,index,o):add('list.get_elem',{'lst':v(lst),'index':index},o)
    def append(lst,item):add('list.append_or_insert',{'lst':v(lst),'insert_way':'append','elem':item})
    def cond(a,op,b):add('workflow.if',{'operand1':a,'operator':op,'operand2':b})
    def loop(lst,o):add('workflow.forin',{'list':v(lst),'output_with_index':False},outputs={'loop_item':o})
    def get(css,o,parent=None,xpath=False,timeout=30):
        i={'browser':v('shop_browser'),'select_type':'xpath_selector' if xpath else 'css_selector','xpath_selector' if xpath else 'css_selector':css,'is_related_parent':bool(parent),'timeout':timeout}
        if parent:i['parent']=v(parent)
        add('web.element.get_element',i,o)
    def all_elements(css,o,parent=None,operation='text',timeout=30):
        i={'browser':v('shop_browser'),'select_type':'css_selector','css_selector':css,'is_related_parent':bool(parent),'operation':operation,'timeout':timeout,'output_with_element_count':False}
        if parent:i['parent']=v(parent)
        add('web.element.get_all_elements',i,outputs={'element_list':o})
    def click(name):add('web.element.click',{'browser':v('shop_browser'),'element':v(name),'simulate':False,'move_mouse':False,'clicks':'click','button':'left','keys':'null','delay_after':0.3,'anchor_type':'center','offset_x':0,'offset_y':0,'timeout':30})
    def input_text(name,text):add('web.element.input',{'browser':v('shop_browser'),'element':v(name),'text':text,'append':False,'input_check':True,'retry_times':1,'simulate':True,'driver_input':False,'save_to_clipboard':False,'input_type':'simulate','contains_hotkey':False,'force_ime_ENG':False,'send_key_delay':30,'delay_after':0.2,'click_before_input':True,'offset_x':0,'offset_y':0,'timeout':30})
    def details(name,operation,o):add('web.element.get_details',{'browser':v('shop_browser'),'element':v(name),'operation':operation,'absolute_url':False,'relative_to':'screen','to96dpi':False,'timeout':30},o)
    def sleep(seconds):add('programing.sleep',{'random_number':False,'seconds':seconds})
    def var(name,value):add('programing.variable',{'value_type':'bool','value':value},name)
    log('[任务开始] 正在打开订单管理页面')
    add('web.create',{'web_type':'chrome','value':URL,'silent_running':False,'wait_load_completed':True,'load_timeout':60,'stop_load_if_load_timeout':'stopLoad','arguments':'--start-maximized'},'shop_browser')
    add('web.browser.get_details',{'browser':v('shop_browser'),'operation':'title'},'window_page_title')
    add('text.append_text_in_newline',{'text':v('window_page_title'),'new_line':False,'new_line_text':'*'},'window_title_pattern')
    add('win32.window.get_window',{'window_type':'win_title_or_class','title':v('window_title_pattern'),'class_name':'Chrome_WidgetWin_1','handle_checked':True,'use_wildcard':True},'recording_window')
    add('win32.window.set_state',{'window_type':'window_instance','window':v('recording_window'),'handle_checked':False,'use_wildcard':False,'flag':'maximize'})
    add('win32.window.activate',{'window_type':'window_instance','window':v('recording_window'),'handle_checked':False,'use_wildcard':False})
    log('[窗口准备完成] 浏览器已最大化，开始处理本次需求');sleep(2)
    add('web.browser.get_details',{'browser':v('shop_browser'),'operation':'url'},'current_url')
    cond(v('current_url'),'in','/user/login')
    log('[网页准备] 使用练习网站的正常凭证入口登录')
    get('button.get-password-btn','credential_button');click('credential_button');sleep(2)
    get('#username','username_input');input_text('username_input','admin')
    get('button.login-button','login_button');click('login_button')
    add('workflow.endif')
    get('table .ant-table-tbody','orders_table',timeout=90)
    log('[查询开始] 正在输入商品名称并查询')
    get('input[placeholder="商品名称"]','product_input');input_text('product_input',product)
    get("//button[.//span[normalize-space(.)='查 询']]",'query_button',xpath=True);click('query_button')
    add('list.create',o='raw_pages');add('list.create',o='accepted_rows');add('list.create',o='accepted_ids');add('list.create',o='seen_first_ids')
    j(['\t'.join(HEADERS)],'display_lines')
    var('all_pages_complete',False)
    add('programing.variable',{'value_type':'str','value':'not_checked'},'next_page_class')
    j(list(range(1,(pages or 1000)+1)),'page_numbers');j(list(range(40)),'poll_attempts')
    loop('page_numbers','page_number')
    var('page_ready',False)
    loop('poll_attempts','poll_attempt')
    get('li.ant-pagination-item-active','active_page');details('active_page','text','active_page_text')
    add('json.to_json',{'text':v('active_page_text')},'active_page_number')
    cond(v('active_page_number'),'==',v('page_number'))
    all_elements('tbody.ant-table-tbody > tr[data-row-key] td:first-child','visible_ids')
    add('list.get_len',{'lst':v('visible_ids')},'visible_count')
    cond(v('visible_count'),'>',0)
    elem('visible_ids',0,'first_id')
    cond(v('seen_first_ids'),'not in',v('first_id'))
    var('page_ready',True)
    all_elements('tbody.ant-table-tbody > tr[data-row-key] td:nth-child(2)','visible_products')
    loop('visible_products','visible_product');cond(v('visible_product'),'!=',product);var('page_ready',False);add('workflow.endif');add('workflow.endloop')
    cond(v('page_ready'),'==',True);append('seen_first_ids',v('first_id'));add('workflow.break');add('workflow.endif')
    add('workflow.endif');add('workflow.endif');add('workflow.endif');sleep(0.5);add('workflow.endloop')
    cond(v('page_ready'),'==',False);add('programing.raise',{'reason':'查询或翻页等待超时；页面未更新或商品筛选不一致，未导出旧数据'});add('workflow.endif')
    log('[页面已就绪] 正在提取当前页订单');sleep(1)
    all_elements('tbody.ant-table-tbody > tr[data-row-key]','order_elements',operation='element')
    add('list.create',o='page_rows')
    loop('order_elements','order_element')
    all_elements('td','cells',parent='order_element')
    for index,name in enumerate(['order_id','product','amount_text','order_date','order_status']):elem('cells',index,name)
    add('list.create',o='raw_row')
    for name in ['order_id','product','amount_text','order_date','order_status']:append('raw_row',v(name))
    append('page_rows',v('raw_row'))
    cond(v('product'),'==',product);cond(v('order_status'),'==','完成');cond(v('accepted_ids'),'not in',v('order_id'))
    add('text.replace_content_from_text',{'text':v('amount_text'),'replace_way':'custom','regular_pattern':'[¥￥,\\s]','replace_text':'','dest_text':'','just_get_first':False,'ignore_case':False,'new_ignore_case':False},'amount_number_text')
    add('json.to_json',{'text':v('amount_number_text')},'amount_number')
    add('list.create',o='accepted_row')
    for name in ['order_id','product','amount_number','order_date','order_status']:append('accepted_row',v(name))
    append('accepted_rows',v('accepted_row'));append('accepted_ids',v('order_id'))
    add('list.create',o='display_row')
    for name in ['order_id','product','amount_number_text','order_date','order_status']:append('display_row',v(name))
    add('text.join_list_to_text',{'list_to_join':v('display_row'),'delimiter_way':'standard','standard_delimiter':'tab','num_standard_delimiter':1},'display_tsv_row')
    append('display_lines',v('display_tsv_row'))
    add('workflow.endif');add('workflow.endif');add('workflow.endif');add('workflow.endloop')
    append('raw_pages',v('page_rows'));log('[订单采集完成] 页码：');log(v('page_number'))
    get('li.ant-pagination-next','next_page_item')
    add('web.element.get_details',{'browser':v('shop_browser'),'element':v('next_page_item'),'operation':'other','attribute_name':'class','absolute_url':False,'relative_to':'screen','to96dpi':False,'timeout':30},'next_page_class')
    cond(v('next_page_class'),'in','ant-pagination-disabled');var('all_pages_complete',True);add('workflow.break');add('workflow.endif')
    cond(pages,'>',0);cond(v('page_number'),'>=',pages);add('workflow.break');add('workflow.endif');add('workflow.endif')
    cond(True,'==',True);get('li.ant-pagination-next:not(.ant-pagination-disabled)','next_button');click('next_button');add('workflow.endif');add('workflow.endloop')
    cond(pages,'==',0);cond(v('all_pages_complete'),'==',False);add('programing.raise',{'reason':'未取得最后一页完成标记，停止并保留证据，不导出不完整报表'});add('workflow.endif');add('workflow.endif')
    add('list.create',o='pagination_proof')
    add('list.get_len',{'lst':v('raw_pages')},'actual_page_count')
    for item in ['all_pages_complete','next_page_class','actual_page_count']:append('pagination_proof',v(item))
    add('json.to_text',{'json_obj':v('pagination_proof')},'pagination_text')
    add('file.write',{'path':str(raw_output.with_name(raw_output.stem+'_分页核验.json')),'content':v('pagination_text'),'write_way':'overwrite','is_text':True,'new_line':False,'encoding':'UTF-8'})
    add('json.to_text',{'json_obj':v('raw_pages')},'raw_text');add('file.write',{'path':str(raw_output),'content':v('raw_text'),'write_way':'overwrite','is_text':True,'new_line':False,'encoding':'UTF-8'})
    log('[采集完成] 正在打开报表窗口')
    asset=Path(__file__).parent/'assets/shop-report-empty.xlsx'
    add('file.copy',{'source_file_paths':str(asset),'copyto_dir_path':str(output.parent),'copy_way':'not_copy'})
    add('file.rename',{'path':str(output.parent/asset.name),'new_name':output.name})
    add('system.run_or_open',{'application_path':str(output),'after_application_launch':'continue','start_as_admin':False,'window_style':'maximized'})
    sleep(2)
    add('win32.window.get_window',{'window_type':'win_title_or_class','title':output.stem+'*','class_name':'XLMAIN','handle_checked':True,'use_wildcard':True},'report_window')
    add('win32.window.set_state',{'window_type':'window_instance','window':v('report_window'),'handle_checked':False,'use_wildcard':False,'flag':'maximize'})
    add('win32.window.activate',{'window_type':'window_instance','window':v('report_window'),'handle_checked':False,'use_wildcard':False})
    log('[表格已打开] 已最大化，开始写入订单数据');sleep(2)
    add('text.join_list_to_text',{'list_to_join':v('display_lines'),'delimiter_way':'standard','standard_delimiter':'new_line','num_standard_delimiter':1},'report_tsv')
    add('clipboard.set_text',{'text':v('report_tsv')})
    def keys(text):add('win32.send_keys',{'keys':text,'hardware_driver_input':False,'force_ime_eng':True,'contains_hotkey':True,'send_key_delay':80,'delay_after':0.8})
    keys('^{Home}');keys('^v');sleep(2);keys('^{Home}');keys('^s');sleep(2)
    add('list.get_len',{'lst':v('accepted_rows')},'matched_count')
    add('win32.window.activate',{'window_type':'window_instance','window':v('report_window'),'handle_checked':False,'use_wildcard':False})
    log('[报表已保存] 表格保持打开，可直接查看')
    log('[订单报表已保存] 符合条件的订单数：');log(v('matched_count'))
    return {'flow_id':'PENDING','blocks':blocks}

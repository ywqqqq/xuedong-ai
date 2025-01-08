from tabulate import tabulate
import sqlite3
from contextlib import contextmanager
import os

@contextmanager
def get_db_connection(db_path):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"数据库文件 '{db_path}' 不存在")
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()

def show_tables(db_path='your_database.db', specific_tables=None):
    """显示数据库中所有表的内容
    
    Args:
        db_path (str): 数据库文件路径
        specific_tables (list): 指定要显示的表名列表，如果为None则显示所有表
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                print("数据库中没有找到任何表")
                return
                
            # 过滤指定的表
            if specific_tables:
                tables = [table for table in tables if table[0] in specific_tables]
                if not tables:
                    print("未找到指定的表")
                    return
            
            # 显示每个表的内容
            for table in tables:
                table_name = table[0]
                if(table_name == 'message'): 
                    continue
                print(f"\n{'='*20} {table_name} {'='*20}")
                
                try:
                    # 获取表中的所有行
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    # 获取列名
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    headers = [column[1] for column in cursor.fetchall()]
                    
                    if rows:
                        print(tabulate(rows, headers=headers, tablefmt='grid'))
                        print(f"总行数: {len(rows)}")
                    else:
                        print("(空表)")
                except sqlite3.Error as e:
                    print(f"读取表 {table_name} 时出错: {e}")
                
                print(f"{'='*50}\n")
                
    except Exception as e:
        print(f"错误: {e}")

def show_message_table(db_path='your_database.db', page_size=10):
    """分页显示数据库中message表的内容
    
    Args:
        db_path (str): 数据库文件路径
        page_size (int): 每页显示的行数
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # 验证message表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
            if not cursor.fetchone():
                print("数据库中未找到message表")
                return
            
            # 获取列名
            cursor.execute("PRAGMA table_info(message)")
            columns = cursor.fetchall()
            headers = [column[1] for column in columns]
            
            # 获取总行数
            cursor.execute("SELECT COUNT(*) FROM message")
            total_rows = cursor.fetchone()[0]
            
            if total_rows == 0:
                print("\n(暂无消息记录)")
                return
                
            # 显示表格结构
            print("\n表格结构:")
            for i, col in enumerate(columns):
                print(f"{i+1}. {col[1]} ({col[2]})")
            
            # 让用户选择要显示的列
            print("\n请选择要显示的列编号（用逗号分隔，直接回车显示所有列）：")
            selected = input().strip()
            if selected:
                selected_cols = [headers[int(i)-1] for i in selected.split(',')]
                col_query = ', '.join(selected_cols)
            else:
                selected_cols = headers
                col_query = '*'
            
            current_page = 0
            while True:
                # 清屏（根据操作系统可能需要调整）
                print('\033[2J\033[H')
                
                # 获取当前页的数据
                offset = current_page * page_size
                cursor.execute(f"SELECT {col_query} FROM message LIMIT ? OFFSET ?", 
                             (page_size, offset))
                rows = cursor.fetchall()
                
                if not rows:
                    print("没有更多数据了")
                    break
                
                # 显示表格
                print("\n" + "="*60)
                print(f"第 {current_page + 1} 页 (每页 {page_size} 行，共 {total_rows} 行)")
                print("="*60)
                
                print(tabulate(rows, 
                             headers=selected_cols, 
                             tablefmt='grid',
                             maxcolwidths=[20]*len(selected_cols)))  # 限制列宽
                
                print("\n操作指令：")
                print("n: 下一页")
                print("p: 上一页")
                print("q: 退出")
                print("g <页码>: 跳转到指定页")
                
                cmd = input("\n请输入命令: ").strip().lower()
                if cmd == 'q':
                    break
                elif cmd == 'n':
                    if (current_page + 1) * page_size < total_rows:
                        current_page += 1
                elif cmd == 'p':
                    if current_page > 0:
                        current_page -= 1
                elif cmd.startswith('g '):
                    try:
                        page = int(cmd.split()[1]) - 1
                        if 0 <= page * page_size < total_rows:
                            current_page = page
                        else:
                            print("页码超出范围！")
                    except:
                        print("无效的页码！")
                
    except Exception as e:
        print(f"错误: {e}")

def main():
    # 可以修改为你的数据库文件路径
    db_path = 'tty.db'
    try:
        # 显示所有表
        show_tables(db_path)
        # show_message_table(db_path)
        # 或者显示指定的表
        # show_tables(db_path, specific_tables=['table1', 'table2'])
                    
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
    # show_message_table('tty.db', page_size=10)
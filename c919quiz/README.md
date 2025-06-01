# C919飞机机型培训题库练习系统

这是一个基于Flask的网页应用程序，用于练习C919飞机机型培训题库中的问题。

## 功能特点

- 从Excel题库中加载题目
- 随机练习模式
- 按主题/子主题练习模式
- 实时反馈正确/错误答案
- 测试结果统计和评估
- 响应式设计，适配移动设备

## 安装步骤

1. 确保已安装Python 3.6+
2. 安装所需依赖:

```bash
pip install flask pandas openpyxl
```

3. 把题库文件 "C919飞机机型培训题库.xlsx" 放在 `data` 目录下
4. 运行应用程序:

```bash
python app.py
```

5. 在浏览器中访问 http://127.0.0.1:5000/

## 目录结构

```
c919quiz/
├── app.py          # Flask应用程序
├── data/           # 数据文件夹
│   └── C919飞机机型培训题库.xlsx
├── static/         # 静态资源
│   └── css/        
│       └── styles.css
└── templates/      # HTML模板
    ├── base.html   # 基础模板
    ├── index.html  # 首页
    ├── quiz.html   # 测试页面
    ├── results.html # 结果页面
    └── topics.html  # 主题选择页面
```

## 使用方法

1. 在首页选择练习模式（随机或按主题）
2. 回答问题，系统会立即给出反馈
3. 完成所有问题后，查看测试结果
4. 可以选择重新开始或按特定主题练习

## 开发者

如需修改或扩展功能，参考Flask文档：https://flask.palletsprojects.com/

## 许可证

仅供个人学习使用
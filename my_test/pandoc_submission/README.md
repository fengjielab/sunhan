# 《制造业自动化》Word转换包

双击`build_word.cmd`，或在PowerShell中运行：

```powershell
& "F:\前途文件\my_test\pandoc_submission\build_word.cmd"
```

输出文件：`my_test/output/制造业自动化投稿稿.docx`。

转换流程会自动完成以下工作：

1. 将现有SVG插图渲染为适合Word的300 dpi灰度PNG；
2. 使用`reference.docx`套用期刊字号、字体、行距和A4版式；
3. 使用`journal.lua`生成上标参考文献序号和右对齐公式编号；
4. 将`\(...\)`行内参数解释和独立公式写入DOCX原生OMML结构；
5. 将图片和表格写入DOCX原生结构。

实验平台实物图尚未提供，因此图1仍为待补占位。补图后，可将占位Div替换为与其他插图相同的Markdown图片语法，再重新运行脚本。

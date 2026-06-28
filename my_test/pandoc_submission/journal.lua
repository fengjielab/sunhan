-- Pandoc filter for the Manufacturing Automation submission manuscript.

local function custom_style(el)
  if el.attributes then
    return el.attributes["custom-style"]
  end
  return nil
end

local function citation_str(el)
  local text = el.text
  local out = {}
  local pos = 1
  local changed = false

  while true do
    local s, e = text:find("%[%d+[%d%-,]*%]", pos)
    if not s then break end
    if s > pos then table.insert(out, pandoc.Str(text:sub(pos, s - 1))) end
    local cite = text:sub(s, e):gsub("%-", "−")
    table.insert(out, pandoc.Superscript({pandoc.Str(cite)}))
    pos = e + 1
    changed = true
  end

  if not changed then return nil end
  if pos <= #text then table.insert(out, pandoc.Str(text:sub(pos))) end
  return out
end

local function equation_para(el)
  if #el.content ~= 1 or el.content[1].t ~= "Math" then return nil end
  local math = el.content[1]

  local number = math.text:match("\\tag%s*{%s*(%d+)%s*}")
  if not number then return nil end
  local source = math.text:gsub("\\tag%s*{%s*%d+%s*}", "")
  source = source:gsub("^%s+", ""):gsub("%s+$", "")

  local tab = pandoc.RawInline("openxml", "<w:r><w:tab/></w:r>")
  local line = pandoc.Para({
    tab,
    pandoc.Math("InlineMath", "\\displaystyle " .. source),
    tab,
    pandoc.Str("(" .. number .. ")")
  })
  return pandoc.Div({line}, pandoc.Attr("", {}, {{"custom-style", "Equation"}}))
end

local function label_span_for(div)
  local labels = {
    ["Abstract Body"] = "Abstract Label",
    ["Keywords"] = "Abstract Label",
    ["Classification"] = "Abstract Label",
    ["English Abstract"] = "English Label",
    ["English Keywords"] = "English Label"
  }
  local label_style = labels[custom_style(div)]
  if not label_style then return div end

  for _, block in ipairs(div.content) do
    if (block.t == "Para" or block.t == "Plain") and #block.content > 0 then
      local first = block.content[1]
      if first.t == "Strong" then
        block.content[1] = pandoc.Span(
          first.content,
          pandoc.Attr("", {}, {{"custom-style", label_style}})
        )
      end
      break
    end
  end
  return div
end

function Pandoc(doc)
  local transformed = {}
  for _, block in ipairs(doc.blocks) do
    if block.t == "Div" and custom_style(block) == "References" then
      table.insert(transformed, block)
    else
      local equation = block.t == "Para" and equation_para(block) or nil
      if equation then
        table.insert(transformed, equation)
      else
        local walked = block:walk({Str = citation_str, Para = equation_para})
        table.insert(transformed, walked)
      end
    end
  end
  doc.blocks = transformed
  doc = doc:walk({Div = label_span_for})
  return doc
end

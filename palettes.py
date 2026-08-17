# palettes.py — Built-in palettes plus dimension/import helpers
# Format: palette_name -> list of 9 hex codes [11,12,13,21,22,23,31,32,33]

PALETTES = {
    "Bluegill":           ["#d3d3d3","#b59a7a","#976020","#a4bdbb","#8c8a6c","#75561c","#74a7a3","#647a5e","#534c19"],
    "BlueGold":           ["#d3d3d3","#d8bd75","#dea301","#8fb1c2","#929f6c","#968901","#488fb0","#498062","#4c6e01"],
    "BlueOr":             ["#d3d3d3","#7ebbd2","#169dd0","#d8a386","#819185","#167984","#dd6a29","#845e29","#174f28"],
    "BlueYl":             ["#d3d3d3","#74b1d6","#0088d9","#d6cb7d","#76ab7e","#008380","#d9be00","#78a000","#007b00"],
    "Brown":              ["#e8e8e8","#cbb8d7","#9972af","#e4d9ac","#c8ada0","#976b82","#c8b35a","#af8e53","#804d36"],
    "Brown2":             ["#d3d3d3","#af9cb9","#8b689f","#c5bb93","#a38b81","#825c6f","#b6a352","#977948","#78503e"],
    "DkBlue":             ["#e8e8e8","#dfb0d6","#be64ac","#ace4e4","#a5add3","#8c62aa","#5ac8c8","#5698b9","#3b4994"],
    "DkBlue2":            ["#d3d3d3","#c098b9","#ad5b9c","#97c5c5","#898ead","#7c5592","#52b6b6","#4a839f","#434e87"],
    "DkCyan":             ["#e8e8e8","#b8d6be","#73ae80","#b5c0da","#90b2b3","#5a9178","#6c83b5","#567994","#2a5a5b"],
    "DkCyan2":            ["#d3d3d3","#9eb9a4","#699e74","#9aa5bb","#739091","#4c7c67","#6277a5","#4a6880","#31595b"],
    "DkViolet":           ["#cabed0","#89a1c8","#4885c1","#bc7c8f","#806a8a","#435786","#ae3a4e","#77324c","#3f2949"],
    "DkViolet2":          ["#d3d3d3","#8aa6c2","#4279b0","#ba8890","#7a6b84","#3a4e78","#9e3547","#682a41","#311e3b"],
    "GrPink":             ["#e8e8e8","#b0d5df","#64acbe","#e4acac","#ad9ea5","#627f8c","#c85a5a","#985356","#574249"],
    "GrPink2":            ["#d3d3d3","#98b8c0","#5b9cad","#c59595","#8e8288","#556f7a","#b65252","#83474a","#4e3d43"],
    "PinkGrn":            ["#d3d3d3","#ca85af","#bc177d","#90b87e","#8a7469","#80144b","#459b22","#42611c","#3e1114"],
    "PurpleGrn":          ["#d3d3d3","#a180ac","#6f2d85","#70a985","#55676c","#3b2454","#027a2e","#014a26","#011a1d"],
    "PurpleOr":           ["#d3d3d3","#9283ac","#563787","#d39c75","#926160","#56284b","#d25601","#923601","#551601"],
    "PinkGrn2":           ["#F7FCF5","#F78FB6","#F73593","#A5E8CD","#A58FB6","#A53593","#40DBA7","#408FA7","#403593"],
    "BlueRed":            ["#D2DEEE","#84A6D9","#366EC3","#D797A3","#877194","#374B85","#D72528","#871C25","#371321"],
    "GrenYellow":         ["#EAF1EB","#9CF9E1","#00F9BB","#F0DF79","#A0E673","#00E660","#F0C600","#A0CC00","#00CC00"],
    "GreenPurple":        ["#EEFEE2","#ABD8F1","#65AFFE","#C6DE8D","#8D9F9B","#7263A9","#9EBE39","#79794C","#78379B"],
    "BlueYellowBlack":    ["#E7E5F1","#F2D279","#F2B200","#A1C7DA","#8D916D","#795900","#4F9CC1","#274E60","#020202"],
    "PaleRedBlue":        ["#F1F1F1","#F8B7B7","#FE7272","#A2EBF3","#A598D4","#935B8F","#62E7F4","#5593D4","#593FB3"],
    "GreenPinkPurple":    ["#F2F2F2","#CADA92","#A1C226","#E5B2EA","#B19C90","#75936A","#D571E0","#7F6FAD","#4B62A2"],
    "BlueGreenPurple":    ["#F3FFE9","#BBE1F4","#86C0FE","#D2E6A6","#A5B3B1","#8E83BB","#B2CC61","#959470","#955EB0"],
    "BlueYellow":         ["#E9E9EB","#A3C6DA","#55A5C7","#ECD088","#A6B37E","#579574","#F5B903","#AEA003","#5D8103"],
    "BlueOrange":         ["#FEF2E5","#97D1E8","#18AFE5","#FAB186","#B0988D","#407A8F","#F3742C","#AB5E36","#5C463C"],
    "PaleblueRed":        ["#E6F9FF","#EBADC8","#F2467E","#99D7F0","#9D96BC","#A13D77","#46B4E0","#487DB0","#4A336F"],
    "PurpleGreen2":       ["#F1EBFF","#C3B5E9","#9580D4","#AEDDB7","#8CAAA7","#6B7898","#60CC63","#4E9C5A","#3B6F52"],
}

CODE_LABELS = {
    "11": "Low A, Low B",    "12": "Low A, Mid B",    "13": "Low A, High B",
    "21": "Mid A, Low B",    "22": "Mid A, Mid B",    "23": "Mid A, High B",
    "31": "High A, Low B",   "32": "High A, Mid B",   "33": "High A, High B",
}


import json
import re

SUPPORTED_DIMS = (3, 4, 5)


def class_codes(dim, vector=True):
    if dim not in SUPPORTED_DIMS:
        raise ValueError('Dimension must be 3, 4, or 5')
    if vector:
        return [f'{chr(65 + x)}{y + 1}' for x in range(dim) for y in range(dim)]
    return [f'{x + 1}{y + 1}' for x in range(dim) for y in range(dim)]


def code_label(code, dim):
    levels = ['Low', 'Low-mid', 'Middle', 'Mid-high', 'High']
    if code[0].isalpha():
        x, y = ord(code[0].upper()) - 65, int(code[1:]) - 1
    else:
        x, y = int(code[0]) - 1, int(code[1:]) - 1
    picks = [0, 2, 4] if dim == 3 else ([0, 1, 3, 4] if dim == 4 else range(5))
    return f'{levels[picks[x]]} A, {levels[picks[y]]} B'


def _rgb(value):
    h = value.strip().lstrip('#')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', h):
        raise ValueError(f'Invalid HEX color: {value}')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return '#{:02X}{:02X}{:02X}'.format(*(max(0, min(255, round(v))) for v in rgb))


def resize_palette(colors, source_dim, target_dim):
    """Bilinearly resize a square palette while preserving all four corners."""
    if source_dim == target_dim:
        return [_hex(_rgb(c)) for c in colors]
    if len(colors) != source_dim * source_dim:
        raise ValueError(f'Expected {source_dim * source_dim} colors, got {len(colors)}')
    grid = [[_rgb(colors[x * source_dim + y]) for y in range(source_dim)]
            for x in range(source_dim)]
    output = []
    for x in range(target_dim):
        sx = x * (source_dim - 1) / (target_dim - 1)
        x0, x1, tx = int(sx), min(source_dim - 1, int(sx) + 1), sx - int(sx)
        for y in range(target_dim):
            sy = y * (source_dim - 1) / (target_dim - 1)
            y0, y1, ty = int(sy), min(source_dim - 1, int(sy) + 1), sy - int(sy)
            rgb = []
            for channel in range(3):
                top = grid[x0][y0][channel] * (1 - ty) + grid[x0][y1][channel] * ty
                bottom = grid[x1][y0][channel] * (1 - ty) + grid[x1][y1][channel] * ty
                rgb.append(top * (1 - tx) + bottom * tx)
            output.append(_hex(rgb))
    return output


def parse_palette_text(text, dim):
    """Read labelled/plain Staridas HEX, CSS, or JSON palette output."""
    raw = (text or '').strip()
    if not raw:
        raise ValueError('No palette colors supplied')
    labelled = re.findall(
        r'["\']?(?:--clr-)?([A-E][1-5])["\']?\s*(?::|=)?\s*["\']?(#[0-9a-fA-F]{6})',
        raw, flags=re.IGNORECASE)
    if labelled:
        found, duplicates = {}, set()
        for code, color in labelled:
            code = code.upper()
            if code in found:
                duplicates.add(code)
            found[code] = color.upper()
        expected = class_codes(dim)
        missing = [c for c in expected if c not in found]
        unexpected = [c for c in found if c not in expected]
        if duplicates:
            raise ValueError('Duplicate palette classes: ' + ', '.join(sorted(duplicates)))
        if missing or unexpected:
            details = []
            if missing:
                details.append('missing ' + ', '.join(missing))
            if unexpected:
                details.append('unexpected ' + ', '.join(unexpected))
            raise ValueError(f'Invalid {dim}×{dim} labelled palette: ' + '; '.join(details))
        return [found[c] for c in expected]
    try:
        obj = json.loads(raw)
        candidates = obj.get('colors', obj.get('palette', obj)) if isinstance(obj, dict) else obj
        flat = []
        if isinstance(candidates, list):
            for item in candidates:
                flat.extend(item if isinstance(item, list) else [item])
        colors = [str(v) for v in flat if re.fullmatch(r'#[0-9a-fA-F]{6}', str(v).strip())]
    except Exception:
        colors = []
    if not colors:
        colors = re.findall(r'#[0-9a-fA-F]{6}', raw)
    expected_count = dim * dim
    if len(colors) != expected_count:
        raise ValueError(f'Expected {expected_count} colors for {dim}×{dim}, found {len(colors)}')
    return [c.upper() for c in colors]


def palette_colors(name, dim, custom_text=''):
    if name == 'Custom / Staridas import':
        return parse_palette_text(custom_text, dim)
    return resize_palette(PALETTES[name], 3, dim)


def transpose_palette(colors, dim=None):
    """Swap X/Y axes for any supported square palette."""
    dim = dim or int(round(len(colors) ** 0.5))
    if dim not in SUPPORTED_DIMS or len(colors) != dim * dim:
        raise ValueError(f'transpose_palette expects a 3×3, 4×4, or 5×5 palette')
    return [colors[row * dim + col] for col in range(dim) for row in range(dim)]

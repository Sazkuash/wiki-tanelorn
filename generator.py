# -*- coding: utf-8 -*-
import yaml
import os
import shutil
import re
from collections import defaultdict

# =========================
# UTILITARIOS
# =========================

def parse_lua_item_info(file_path):
    """Le o import_iteminfo.lua para extrair a Sprite e a Descricao corrigida."""
    item_data = {}
    if not os.path.exists(file_path):
        return item_data
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    block_pattern = re.compile(r'\[(\d+)\]\s*=\s*\{(.*?)\s*\},', re.DOTALL)
    for match in block_pattern.finditer(content):
        item_id = int(match.group(1))
        block_content = match.group(2)
        sprite_match = re.search(r'identifiedResourceName\s*=\s*"([^"]+)"', block_content)
        sprite = sprite_match.group(1) if sprite_match else "N/A"
        desc_pattern = re.compile(r'identifiedDescriptionName\s*=\s*\{(.*?)\}', re.DOTALL)
        desc_match = desc_pattern.search(block_content)
        description = []
        if desc_match:
            lines = re.findall(r'"([^"]*)"', desc_match.group(1))
            description = [re.sub(r'\^[0-9a-fA-F]{6}', '', l).strip() for l in lines if l.strip()]
        item_data[item_id] = {"sprite": sprite, "description": description}
    return item_data

def safe_folder(value, default="Other"):
    if not value: return default
    value = str(value).strip()
    # Mapeamento para evitar caracteres problematicos em nomes de pastas
    aliases = {"petegg": "PetEgg", "shadowgear": "Shadowgear", "weapon": "Weapon", "armor": "Armor"}
    key = value.lower().replace("-", "").replace("_", "").replace(" ", "")
    return aliases.get(key, value)

def write_file(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# =========================
# GERADOR PRINCIPAL
# =========================

def generate():
    print("Iniciando geracao da Wiki...")

    # 1. CARREGAR DADOS
    items = []
    item_files = ["data/item_db_equip.yml", "data/item_db_etc.yml"]
    for f_path in item_files:
        if os.path.exists(f_path):
            print(f"Lendo {f_path}...")
            with open(f_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "Body" in data:
                    items.extend(data["Body"])

    with open("data/mob_db.yml", "r", encoding="utf-8") as f:
        mobs = yaml.safe_load(f)["Body"]

    lua_info = parse_lua_item_info("data/import_iteminfo.lua")

    # 2. MAPEAR RELACOES PARA LINKS CRUZADOS
    item_path_map = {} # ID -> Caminho relativo para o Monstro usar
    aegis_to_id = {}   # AegisName -> ID para processar os drops dos Mobs

    for i in items:
        if not i: continue
        tipo = safe_folder(i.get("Type"))
        subtipo = safe_folder(i.get("SubType", "General"))
        # Caminho que o arquivo do monstro deve usar para chegar no item
        item_path_map[i['Id']] = f"../itens/{tipo}/{subtipo}/{i['Id']}.md"
        aegis_to_id[i['AegisName']] = i['Id']

    # Mapear quem dropa o que (Para a pagina do Item)
    drops_on_item_page = defaultdict(list)
    for m in mobs:
        if not m or "Drops" not in m: continue
        for d in m["Drops"]:
            item_id = aegis_to_id.get(d["Item"])
            if item_id:
                rate = d["Rate"]/100
                # Link do Item para o Monstro
                drops_on_item_page[item_id].append(
                    f"| [{m['Name']}](../../../monstros/{m['Id']}.md) | {rate:.2f}% |"
                )

    # 3. LIMPAR PASTAS ANTIGAS
    for folder in ["docs/itens", "docs/monstros"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # 4. GERAR PAGINAS DE ITENS
    tree = defaultdict(lambda: defaultdict(list))
    for i in items:
        if not i: continue
        tree[safe_folder(i.get("Type"))][safe_folder(i.get("SubType", "General"))].append(i)

    for tipo, subtipos in tree.items():
        for subtipo, itens_lista in subtipos.items():
            for i in itens_lista:
                info = lua_info.get(i['Id'], {"sprite": i['AegisName'], "description": []})
                img = f"../../../assets/collection/{i['Id']}.png"
                
                item_page = [
                    f"# {i['Name']} (ID: {i['Id']})",
                    f"![icon]({img})",
                    f"\n**Sprite:** `{info['sprite']}`",
                    "\n## Descricao Oficial",
                    "> " + "  \n> ".join(info['description']) if info['description'] else "*Sem descricao.*",
                    "\n## Onde Dropar",
                    "| Monstro | Chance |",
                    "|---------|--------|",
                    *drops_on_item_page.get(i["Id"], ["| - | Nao dropado por monstros |"]),
                    "\n## Script", f"```c\n{i.get('Script', 'N/A')}\n```"
                ]
                write_file(f"docs/itens/{tipo}/{subtipo}/{i['Id']}.md", item_page)

    # 5. GERAR PAGINAS DE MONSTROS
    for m in mobs:
        if not m: continue
        img_mob = f"../assets/monsters/{m['Id']}.png"
        
        # Tabela de drops com links para os itens
        mob_drops_table = ["| Item | Chance |", "|------|--------|"]
        if "Drops" in m:
            for d in m["Drops"]:
                it_id = aegis_to_id.get(d["Item"])
                rate = d["Rate"]/100
                if it_id:
                    # Link do Monstro para o Item usando o mapa de caminhos
                    target_link = item_path_map[it_id]
                    mob_drops_table.append(f"| [{d['Item']}]({target_link}) | {rate:.2f}% |")
                else:
                    mob_drops_table.append(f"| {d['Item']} | {rate:.2f}% |")

        mob_page = [
            f"# {m['Name']} (ID: {m['Id']})",
            f"![mob]({img_mob})",
            "\n## Atributos",
            f"| Nivel | HP | Raca | Elemento |",
            f"|-------|----|------|----------|",
            f"| {m.get('Level')} | {m.get('Hp')} | {m.get('Race')} | {m.get('Element')} |",
            "\n## Drops (Clique no item para ver detalhes)",
            *mob_drops_table
        ]
        write_file(f"docs/monstros/{m['Id']}.md", mob_page)

    print("Wiki gerada com sucesso!")

if __name__ == "__main__":
    generate()
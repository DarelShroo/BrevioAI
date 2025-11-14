import ast
import os
import sys
from typing import Any, Dict, List, Set


def get_imports(file_path: str) -> Set[str]:
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                for name in node.names:
                    if module:
                        imports.add(f"{module}.{name.name}")
                    else:
                        imports.add(name.name)
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
    return imports


def simplify_path(path: str) -> str:
    if "/core/brevio/services/" in path:
        return os.path.basename(path)
    elif "/core/brevio/models/" in path:
        return "models/" + os.path.basename(path)
    elif "/core/brevio/enums/" in path:
        return "enums/" + os.path.basename(path)
    elif "/core/brevio/utils/" in path:
        return "utils/" + os.path.basename(path)
    elif "/core/shared/" in path:
        return "shared/" + "/".join(path.split("/shared/")[-1].split("/"))
    else:
        return "/".join(path.split("/")[-2:])


def create_dependency_graph(files: List[str]) -> None:
    print("digraph G {")
    print("  rankdir=LR;")
    print("  compound=true;")
    print("  node [shape=box, style=filled, fillcolor=lightblue, fontsize=10];")
    print("  ranksep=1.5;")
    print("  nodesep=0.5;")

    # Definir clusters
    clusters: Dict[str, Dict[str, Any]] = {
        "services": {"color": "lightblue", "files": []},
        "models": {"color": "lightgreen", "files": []},
        "enums": {"color": "lightyellow", "files": []},
        "utils": {"color": "lightpink", "files": []},
        "shared": {"color": "lightgrey", "files": []},
    }

    # Clasificar archivos
    for file in files:
        if "/tests/" in file or "__init__.py" in file:
            continue

        if "/services/" in file:
            clusters["services"]["files"].append(file)
        elif "/models/" in file:
            clusters["models"]["files"].append(file)
        elif "/enums/" in file:
            clusters["enums"]["files"].append(file)
        elif "/utils/" in file:
            clusters["utils"]["files"].append(file)
        elif "/shared/" in file:
            clusters["shared"]["files"].append(file)

    # Crear nodos en clusters
    file_to_id = {}
    for cluster_name, cluster_info in clusters.items():
        print(f"  subgraph cluster_{cluster_name} {{")
        print(f"    style=filled;")
        print(f'    color={cluster_info["color"]};')
        print(f'    label="{cluster_name}";')

        for i, file in enumerate(cluster_info["files"]):
            file_id = f"{cluster_name}_{i}"
            file_to_id[file] = file_id
            label = simplify_path(file)
            print(f'    {file_id} [label="{label}"];')

        print("  }")

    # Analizar dependencias principales
    for file in files:
        if file not in file_to_id:
            continue

        imports = get_imports(file)
        source_id = file_to_id[file]

        for target_file in files:
            if target_file not in file_to_id or target_file == file:
                continue

            module_path = os.path.splitext(target_file)[0].replace("/", ".")
            if module_path.startswith("./"):
                module_path = module_path[2:]

            for imp in imports:
                if imp in module_path or module_path in imp:
                    target_id = file_to_id[target_file]
                    print(f"  {source_id} -> {target_id} [penwidth=0.5];")
                    break

    print("}")


if __name__ == "__main__":
    files = [line.strip() for line in sys.stdin if line.strip()]
    create_dependency_graph(files)

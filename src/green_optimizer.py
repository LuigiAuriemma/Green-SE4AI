import ast

class GreenTransformer(ast.NodeTransformer):
    """
    Naviga l'albero sintattico per:
    1. Rimuovere docstring.
    2. Offuscare variabili locali.
    3. Rimuovere Type Hints.
    4. Rimuovere stampe, log e asserzioni interne.
    """

    def __init__(self):
        super().__init__()
        self.rename_map = {}
        self.var_counter = 1
        self.excluded_names = set()

    #1. GESTIONE FUNZIONE, PARAMETRI E DOCSTRING
    def visit_FunctionDef(self, node):
        # Proteggiamo il nome della funzione
        self.excluded_names.add(node.name)

        # Rimuoviamo il Type Hint di ritorno (es. -> bool)
        node.returns = None

        # Proteggiamo i parametri di input
        for arg in node.args.args:
            self.excluded_names.add(arg.arg)

        # Rimuoviamo la docstring
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body.pop(0)

        self.generic_visit(node)
        return node

    #2. RIMOZIONE TYPE HINTS
    def visit_arg(self, node):
        # Rimuove il Type Hint dai parametri (es. numero: int diventa numero)
        node.annotation = None
        return node

    def visit_AnnAssign(self, node):
        # Trasforma le variabili tipizzate (x: int = 5) in assegnazioni normali (x = 5)
        if node.value is not None:
            new_node = ast.Assign(targets=[node.target], value=node.value)
            return self.visit(new_node)
        return None  # Rimuove dichiarazioni vuote come "x: int"

    #3. RIMOZIONE STAMPE E LOG
    def visit_Assert(self, node):
        # Distrugge tutte le asserzioni interne
        return None

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call):
            func = node.value.func

            # Cerca e distrugge i print
            if isinstance(func, ast.Name) and func.id == 'print':
                return None

            # Cerca e distrugge i log
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id in ['logging', 'logger']:
                    return None

        self.generic_visit(node)
        return node

    #4. OFFUSCAMENTO VARIABILI
    def visit_Name(self, node):
        if node.id in self.excluded_names:
            return node

        if isinstance(node.ctx, ast.Store):
            if node.id not in self.rename_map:
                self.rename_map[node.id] = f"v{self.var_counter}"
                self.var_counter += 1
            node.id = self.rename_map[node.id]

        elif isinstance(node.ctx, ast.Load):
            if node.id in self.rename_map:
                node.id = self.rename_map[node.id]

        return node


def optimize_code(source_code: str) -> str:
    """Pipeline completa"""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"Errore di sintassi nel codice grezzo: {e}")
        return source_code

    transformer = GreenTransformer()
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)

    return ast.unparse(tree)
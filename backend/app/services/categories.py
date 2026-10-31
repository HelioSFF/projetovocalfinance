CATEGORIES = [
    {"code": "food", "label": "Alimentação", "type": "expense"},
    {"code": "groceries", "label": "Mercado", "type": "expense"},
    {"code": "housing", "label": "Moradia", "type": "expense"},
    {"code": "utilities", "label": "Contas da casa", "type": "expense"},
    {"code": "transport", "label": "Transporte", "type": "expense"},
    {"code": "health", "label": "Saúde", "type": "expense"},
    {"code": "education", "label": "Educação", "type": "expense"},
    {"code": "leisure", "label": "Lazer", "type": "expense"},
    {"code": "shopping", "label": "Compras", "type": "expense"},
    {"code": "clothing", "label": "Vestuário", "type": "expense"},
    {"code": "personal_care", "label": "Cuidados pessoais", "type": "expense"},
    {"code": "pets", "label": "Pets", "type": "expense"},
    {"code": "subscriptions", "label": "Assinaturas", "type": "expense"},
    {"code": "travel", "label": "Viagens", "type": "expense"},
    {"code": "taxes_fees", "label": "Impostos e taxas", "type": "expense"},
    {"code": "gifts_donations", "label": "Presentes e doações", "type": "expense"},
    {"code": "other_expense", "label": "Outras despesas", "type": "expense"},
    {"code": "salary", "label": "Salário", "type": "income"},
    {"code": "freelance", "label": "Freelance / serviços", "type": "income"},
    {"code": "sales", "label": "Vendas", "type": "income"},
    {"code": "investments", "label": "Rendimentos", "type": "income"},
    {"code": "refunds", "label": "Reembolsos", "type": "income"},
    {"code": "gifts_received", "label": "Presentes recebidos", "type": "income"},
    {"code": "other_income", "label": "Outras receitas", "type": "income"},
]

CATEGORY_LABELS = {entry["code"]: entry["label"] for entry in CATEGORIES}


def category_label(code: str) -> str:
    return CATEGORY_LABELS.get(code, code)

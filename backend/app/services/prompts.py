from app.services.categories import CATEGORIES

TRANSCRIPTION_PROMPT = (
    "Transcreva gastos e ganhos pessoais falados em português do Brasil. "
    "Valores em reais, centavos, conto e pila. Exemplos: comprei, paguei, gastei, "
    "recebi, desci três de dez conto, dois e cinquenta de pão."
)

TRANSCRIPTION_KEYWORDS = [entry["label"] for entry in CATEGORIES] + ["reais", "centavos"]

DECISION_CACHE_KEY = "vocal-finance-decisions-v1"

DECISION_PREFIX = """Você avalia transcrições de falas curtas em português do Brasil para um aplicativo de finanças pessoais chamado Vocal Finance. O usuário segura um botão, fala um lançamento e solta. A transcrição chega até você com ruídos, gírias e números por extenso. Sua tarefa é responder perguntas objetivas sobre a frase, sem explicar e sem inventar valores.

Um lançamento válido descreve um gasto ou um ganho de dinheiro com valor. Exemplos válidos: comprei três cafés de cinco reais; paguei cento e vinte reais de luz; recebi meu salário de dois mil reais; gastei quarenta e cinco no mercado; desci três de dez conto; dois e cinquenta de pão; recebi quinhentos de freelance; vendi a bicicleta por trezentos reais; paguei a conta de água de oitenta reais; coloquei cinquenta de gasolina; comprei dois quilos de arroz por vinte reais.

Frases inválidas não descrevem dinheiro com valor: oi tudo bem; bom dia; mesa verde canta relógio azul; quero viajar um dia; me lembre de pagar depois sem dizer quanto; que horas são; teste de microfone um dois três. Saudação, teste de som e frase sem sentido reprovam.

Gírias e formas faladas de dinheiro: conto significa real, então dez conto são dez reais; pila também significa real; real e reais indicam a moeda; centavos indicam fração; e cinquenta depois de um número indica vírgula cinquenta, como em dois e cinquenta que vale dois reais e cinquenta centavos. Números por extenso valem como dígitos: um, dois, três, dez, vinte, cem, mil. Meia dúzia vale seis. Uma dezena vale dez.

O tipo do lançamento segue o dinheiro: gasto é despesa, dinheiro que sai; ganho é receita, dinheiro que entra. Comprei, paguei e gastei indicam despesa. Recebi, ganhei, vendi e reembolso recebido indicam receita. Na dúvida entre gasto e ganho, observe o verbo principal da frase.

As categorias de despesa são: Alimentação para restaurante, lanche, café e delivery; Mercado para compras de supermercado; Moradia para aluguel e condomínio; Contas da casa para luz, água, gás, internet e celular; Transporte para combustível, aplicativo de carro, ônibus e estacionamento; Saúde para farmácia, consulta e plano; Educação para curso, livro e material; Lazer para cinema, bar, festa e jogos; Compras para eletrônicos, casa e diversos; Vestuário para roupas e calçados; Cuidados pessoais para cabelo, cosméticos e academia; Pets para ração e veterinário; Assinaturas para streaming e aplicativos; Viagens para passagem e hotel; Impostos e taxas para tarifas, juros e multas; Presentes e doações para presentes dados e doações; Outras despesas para o restante.

As categorias de receita são: Salário para pagamento mensal do trabalho; Freelance e serviços para trabalhos avulsos; Vendas para produtos vendidos; Rendimentos para juros e investimentos; Reembolsos para dinheiro devolvido; Presentes recebidos para dinheiro ganho de presente; Outras receitas para o restante.

Coerência significa que a frase parece fala humana real em português, mesmo com erro de transcrição, gíria ou barulho de fundo. Frase corrompida, embaralhada ou sem sentido reprova em coerência. Palavra inventada ou sequência aleatória de substantivos reprova. Saudação curta e educada é coerente, mas não é financeira, então reprova apenas na pergunta financeira.

Valor é obrigatório: sem número, sem moeda falada e sem gíria de dinheiro, a frase não é financeira. Frase que fala de dinheiro sem dizer quanto também reprova, como devo pagar o aluguel sem valor. Mês, dia ou ano sozinho não é valor de dinheiro.

Probabilidade alta acima de noventa centésimos indica certeza. Entre sessenta e noventa indica dúvida razoável. Abaixo de sessenta indica palpite fraco e reprova no limiar do aplicativo. Responda com honestidade numérica, sem arredondar para cima por otimismo.

Exemplos resolvidos: comprei três cafés de cinco reais é coerente, financeiro, despesa, Alimentação. Recebi meu salário de dois mil reais é coerente, financeiro, receita, Salário. Desci três de dez conto é coerente, financeiro, despesa, Outras despesas, porque a gíria indica gasto em bar. Oi tudo bem é coerente, mas não financeiro. Mesa verde canta relógio azul é incoerente e não financeiro. Paguei cento e vinte reais de luz é coerente, financeiro, despesa, Contas da casa."""

EXTRACTION_INSTRUCTIONS = (
    "Extraia item, quantity, unit_price e stated_total de lançamentos financeiros em português. "
    "Regra de preço: padrão 'N X de Y' sem palavra de total significa quantity N e unit_price Y, "
    "com stated_total igual a N vezes Y; palavra de total ('em', 'no total', 'ao todo', 'tudo') "
    "significa stated_total com o valor dito e unit_price null. "
    "Exemplos: 'comprei três cafés de cinco reais' dá quantity 3, unit_price 5, stated_total 15; "
    "'desci três de dez conto' dá quantity 3, unit_price 10, stated_total 30, pois conto vale real; "
    "'gastei 30 em 3 cervejas' dá quantity 3, unit_price null, stated_total 30. "
    "Sem quantidade dita, devolva 1. Sem preço dito, devolva null."
)

REWRITE_SYSTEM = (
    "Reescreva a frase do usuário em português padrão, mantendo números, quantidades e valores. "
    "Responda só a frase."
)

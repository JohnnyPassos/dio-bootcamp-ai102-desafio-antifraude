# Validador de Faturas com Azure AI Document Intelligence (Python)

Este projeto lê faturas (PDF/Imagem) usando o Azure AI Document Intelligence (modelo `prebuilt-invoice`) e aplica regras de validação para aprovar ou reprovar o documento.  
As validações incluem:
- Presença de campos essenciais (InvoiceId, VendorName, InvoiceDate, InvoiceTotal, etc.)
- Confiança mínima nos campos
- Verificação do total (soma de itens com tolerância em relação ao `InvoiceTotal`)
- Lista de fornecedores permitidos
- Coerência de datas (DueDate >= InvoiceDate)

Baseado na documentação oficial do Azure AI em repositórios GitHub da Microsoft:
- Azure SDK para Python – Document Intelligence:  
  - Código e pacotes: https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/documentintelligence/azure-ai-documentintelligence
  - Exemplos e guias: https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/documentintelligence/azure-ai-documentintelligence/samples
- Serviço Document Intelligence (Form Recognizer):  
  - Documentação do serviço: https://learn.microsoft.com/azure/ai-services/document-intelligence/
  - Referência do SDK Python: https://learn.microsoft.com/python/api/overview/azure/ai-documentintelligence-readme

## Requisitos

- Python 3.10+ (recomendado 3.11)
- Uma instância do Azure AI Document Intelligence com:
  - Endpoint
  - API Key
- Permissões de rede para acessar o endpoint

## Instalação

1) Clone este repositório (ou copie os arquivos do projeto).

2) Crie um ambiente virtual e instale dependências:
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows PowerShell

pip install -r requirements.txt
```

3) Configure variáveis de ambiente:
- Copie `.env.example` para `.env` e preencha com seus valores:
  - `AZURE_DOCUMENTINTELLIGENCE_ENDPOINT`
  - `AZURE_DOCUMENTINTELLIGENCE_KEY`
  - Ajuste demais parâmetros conforme necessário.

4) Configure o PYTHONPATH (para execução local):
```bash
# na raiz do repositório
export PYTHONPATH=$(pwd)/src  # Linux/macOS
# $env:PYTHONPATH=(Get-Location).Path + "\src"  # Windows PowerShell
```

## Uso (CLI)

Analise e valide uma fatura:
```bash
python -m app.main --file ./exemplos/fatura.pdf
```

Saída (JSON):
- `approved`: true/false
- `reasons`: lista de mensagens indicando os motivos da aprovação/reprovação
- `extracted`: campos extraídos da fatura
- `confidences`: confianças por campo
- `items`: itens extraídos (quando presentes)

Código de saída do processo:
- 0 se aprovado
- 2 se reprovado
- 1 em caso de erro de execução

### Parâmetros

```bash
python -m app.main --file <caminho> \
  [--min-confidence 0.6] \
  [--sum-tolerance 0.01] \
  [--require-sum-match] \
  [--vendors-allowlist "Fornecedor A,Fornecedor B"]
```

Observações:
- Parâmetros de CLI sobrescrevem valores do `.env`.
- `--require-sum-match` força reprovação caso soma de itens não bata com o total dentro da tolerância.

## Variáveis de Ambiente (.env)

Veja `.env.example` para a lista completa. Principais:
- `AZURE_DOCUMENTINTELLIGENCE_ENDPOINT` e `AZURE_DOCUMENTINTELLIGENCE_KEY`
- `MIN_CONFIDENCE` (ex.: 0.6)
- `REQUIRE_SUM_MATCH` (true/false)
- `SUM_TOLERANCE` (ex.: 0.01)
- `VENDORS_ALLOWLIST` (lista separada por vírgulas)

## Regras de Validação (resumo)

- Campos obrigatórios presentes: `InvoiceId`, `VendorName`, `InvoiceDate`, `InvoiceTotal`
- Confiança mínima nos campos obrigatórios (configurável)
- Se `REQUIRE_SUM_MATCH=true`:  
  - Se existirem itens, a soma de `Amount` (ou `Quantity * UnitPrice` quando `Amount` não existir) deve bater com `InvoiceTotal` dentro da tolerância (`SUM_TOLERANCE`)
  - Caso não existam itens, checa coerência simplificada entre `SubTotal + TotalTax` (~=) `InvoiceTotal`
- Datas: `DueDate` não deve ser anterior a `InvoiceDate` (quando ambas existem)
- `VendorName` presente na allowlist quando definida

## Notas sobre o SDK e Modelo

- Este projeto utiliza o modelo `prebuilt-invoice` do Document Intelligence.
- Pacote Python: `azure-ai-documentintelligence`
- Classe principal: `DocumentIntelligenceClient`
- Método: `begin_analyze_document(model_id="prebuilt-invoice", ...)

Para detalhes, exemplos e atualizações, consulte os repositórios GitHub oficiais e a documentação do serviço (links acima).

## Docker (opcional)

Build e uso com Docker:
```bash
docker build -t invoice-validator .
# passe o .env e monte o arquivo a analisar
docker run --rm --env-file .env -v $(pwd):/work -w /work invoice-validator --file ./exemplos/fatura.pdf
```

## Licença

Uso educacional/exemplo. Adapte conforme sua necessidade.
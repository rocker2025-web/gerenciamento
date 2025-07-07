# pages/3_Elaboracao_de_Contratos.py
import streamlit as st
import utils
import pandas as pd
from datetime import date
import uuid # Import para gerar IDs únicos

st.set_page_config(page_title="Elaboração de Contratos", layout="wide")

# --- VERIFICAÇÃO DE AUTENTICAÇÃO E LOGOUT ---
if not st.session_state.get('autenticado'):
    st.error("Acesso negado. Por favor, realize o login.")
    st.stop()

with st.sidebar:
    st.success(f"Bem-vindo, {st.session_state.get('nome_usuario')}!")
    if st.button("Logout"):
        st.session_state.clear()
        st.switch_page("1_Login.py")

st.title("Elaboração de Contratos")

# --- CONEXÃO COM BANCOS DE DADOS ---
try:
    drive = utils.login_gdrive()
    clients_file = utils.get_database_file(drive, "clients.json")
    clientes_data = utils.read_data(clients_file)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()
    
# Inicializa a lista de itens do contrato na sessão
if 'itens_contrato' not in st.session_state:
    st.session_state.itens_contrato = [{'id': 0}]

# --- Formulário Principal ---
with st.form("form_contrato", clear_on_submit=False):
    st.subheader("Dados Gerais do Contrato")
    
    tipo_contrato = st.radio("Tipo de Contrato", ["Locação", "Venda"], horizontal=True, key="tipo_contrato")
    
    # Prepara a lista de clientes para o selectbox
    lista_clientes = {f"{c['nome_razao_social']} - {c['cpf_cnpj']}": c['id'] for c in clientes_data}
    cliente_selecionado_label = st.selectbox("Selecione o Cliente", options=lista_clientes.keys(), key="cliente_selecionado")
    
    st.markdown("---")
    st.subheader("Itens do Contrato")

    # Loop para criar os campos de cada item dinamicamente
    for i, item in enumerate(st.session_state.itens_contrato):
        with st.container(border=True):
            st.write(f"**Item {i + 1}**")
            cols_item = st.columns([3, 2, 1])
            cols_item[0].selectbox("Produto", ["BALANCIM SUSPENSO ULTRALEVE MANUAL", "BALANCIM SUSPENSO ULTRALEVE ELÉTRICO"], key=f"produto_{i}")
            cols_item[1].selectbox("Tamanho da Plataforma", ["PLATAFORMA DE 1 METRO", "PLATAFORMA DE 2 METROS", "PLATAFORMA DE 3 METROS", "PLATAFORMA DE 4 METROS", "PLATAFORMA DE 5 METROS", "PLATAFORMA DE 6 METROS", "PLATAFORMA DE 8 METROS"], key=f"plataforma_{i}")
            cols_item[2].number_input("Quantidade", min_value=1, value=1, key=f"quantidade_{i}")
            
            st.number_input("Valor Unitário Mensal (R$)", min_value=0.0, format="%.2f", key=f"valor_unitario_{i}")

    # Este botão agora submete o formulário para adicionar um item.
    # A lógica de clique está no `on_click`
    st.form_submit_button("Adicionar Outro Produto", on_click=lambda: st.session_state.itens_contrato.append({'id': len(st.session_state.itens_contrato)}))
    
    st.markdown("---")
    st.subheader("Detalhes Finais")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        valor_entrega = st.number_input("Valor de Entrega (R$)", min_value=0.0, format="%.2f", key="valor_entrega")
    with col_t2:
        valor_recolha = st.number_input("Valor de Recolhimento (R$)", min_value=0.0, format="%.2f", key="valor_recolha")

    endereco_obra = st.text_area("Endereço da Obra", key="endereco_obra")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        contato_nome = st.text_input("Nome do Contato na Obra", key="contato_nome")
    with col_c2:
        contato_telefone = st.text_input("Telefone do Contato", key="contato_telefone")
        
    data_inicio = st.date_input("Data de Início da Locação", value=date.today(), key="data_inicio")

    # Botão de submissão final
    submitted = st.form_submit_button("Gerar Documento do Contrato")

# A lógica de submissão agora fica fora do form
if submitted:
    cliente_id = st.session_state.get("cliente_selecionado") and lista_clientes.get(st.session_state.cliente_selecionado)
    cliente_obj = next((c for c in clientes_data if c['id'] == cliente_id), None)
    
    if cliente_obj:
        # Coleta os dados dos itens dinâmicos da sessão
        itens_para_contrato = []
        for i in range(len(st.session_state.itens_contrato)):
            item_data = {
                'produto': st.session_state.get(f"produto_{i}"),
                'plataforma': st.session_state.get(f"plataforma_{i}"),
                'quantidade': st.session_state.get(f"quantidade_{i}"),
                'valor_unitario': st.session_state.get(f"valor_unitario_{i}")
            }
            itens_para_contrato.append(item_data)
        
        # Gera o próximo número de contrato sequencial
        numero_contrato = utils.get_next_contract_number(drive)
        
        if numero_contrato:
            # Monta o dicionário completo com todos os dados do contrato
            dados_contrato = {
                "id_contrato": str(uuid.uuid4()),
                "numero_contrato": numero_contrato,
                "data_geracao": date.today().isoformat(),
                "status": "Ativo", # NOVO: Define o status padrão como "Ativo"
                "tipo_contrato": st.session_state.get("tipo_contrato"),
                "cliente": cliente_obj,
                "itens_contrato": itens_para_contrato,
                "valor_entrega": st.session_state.get("valor_entrega"),
                "valor_recolha": st.session_state.get("valor_recolha"),
                "endereco_obra": st.session_state.get("endereco_obra"),
                "contato_nome": st.session_state.get("contato_nome"),
                "contato_telefone": st.session_state.get("contato_telefone"),
                "data_inicio": st.session_state.get("data_inicio").strftime("%d/%m/%Y"),
                "data_assinatura": date.today().strftime("%d de %B de %Y").lower()
            }

            # --- LÓGICA DE SALVAMENTO NO contracts.json ---
            contracts_file = utils.get_database_file(drive, "contracts.json")
            contratos_existentes = utils.read_data(contracts_file)
            contratos_existentes.append(dados_contrato)
            utils.write_data(contracts_file, contratos_existentes)
            
            # ATUALIZADO: Chama a função a partir de utils para gerar o .docx
            st.session_state.contrato_gerado = utils.gerar_contrato_docx(dados_contrato)
            st.session_state.nome_arquivo_contrato = f"CONTRATO_{numero_contrato}_{cliente_obj['nome_razao_social']}.docx"
            
            st.success("Contrato gerado e salvo com sucesso!")
            # Reseta a lista de itens para um novo contrato
            st.session_state.itens_contrato = [{'id': 0}]
        else:
            st.error("Cliente selecionado não encontrado.")

# Botão de download que aparece após a geração do contrato
if 'contrato_gerado' in st.session_state and st.session_state.contrato_gerado:
    st.download_button(
        label="Baixar Contrato (.docx)",
        data=st.session_state.contrato_gerado,
        file_name=st.session_state.nome_arquivo_contrato,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

utils.exibir_rodape()

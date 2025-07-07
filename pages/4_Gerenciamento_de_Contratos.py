# pages/4_Gerenciamento_de_Contratos.py
import streamlit as st
import utils
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gerenciamento de Contratos", layout="wide")

# --- Função para atualizar o status de um contrato ---
def atualizar_status_contrato(drive, id_contrato, novo_status):
    contracts_file = utils.get_database_file(drive, "contracts.json")
    contratos_data = utils.read_data(contracts_file)
    
    # Encontra o contrato e atualiza o status
    for contrato in contratos_data:
        if contrato['id_contrato'] == id_contrato:
            contrato['status'] = novo_status
            break
            
    # Salva a lista inteira de volta no arquivo
    utils.write_data(contracts_file, contratos_data)
    st.success(f"Status do contrato atualizado para '{novo_status}'.")
    st.rerun()

# --- VERIFICAÇÃO DE AUTENTICAÇÃO E LOGOUT ---
if not st.session_state.get('autenticado'):
    st.error("Acesso negado. Por favor, realize o login.")
    st.stop()

with st.sidebar:
    st.success(f"Bem-vindo, {st.session_state.get('nome_usuario')}!")
    if st.button("Logout"):
        st.session_state.clear()
        st.switch_page("1_Login.py")

st.title("Gerenciamento de Contratos")

# --- CONEXÃO COM BANCOS DE DADOS ---
try:
    drive = utils.login_gdrive()
    contracts_file = utils.get_database_file(drive, "contracts.json")
    contratos_data = utils.read_data(contracts_file)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- FILTROS DE BUSCA ---
st.subheader("Buscar Contratos")
col1, col2, col3 = st.columns(3)
with col1:
    busca_texto = st.text_input("Buscar por Nº do Contrato ou Nome do Cliente")
with col2:
    status_opcoes = ["Todos", "Ativo", "Encerrado", "Encerrado com Pendências"]
    status_selecionado = st.selectbox("Filtrar por Status", options=status_opcoes)
with col3:
    data_hoje = datetime.now().date()
    busca_data = st.date_input("Filtrar por Data de Geração", value=None, max_value=data_hoje)

contratos_filtrados = contratos_data
if busca_texto:
    busca_texto_lower = busca_texto.lower()
    contratos_filtrados = [c for c in contratos_filtrados if busca_texto_lower in c['numero_contrato'].lower() or busca_texto_lower in c['cliente']['nome_razao_social'].lower()]
if status_selecionado != "Todos":
    contratos_filtrados = [c for c in contratos_filtrados if c.get('status') == status_selecionado]
if busca_data:
    contratos_filtrados = [c for c in contratos_filtrados if c['data_geracao'] == busca_data.isoformat()]

st.markdown("---")
st.subheader("Contratos Encontrados")

if not contratos_filtrados:
    st.info("Nenhum contrato encontrado com os filtros atuais.")
else:
    contratos_ordenados = sorted(contratos_filtrados, key=lambda c: c['data_geracao'], reverse=True)
    
    for contrato in contratos_ordenados:
        cliente = contrato['cliente']
        status_atual = contrato.get('status', 'N/A')
        
        # Define a cor do expander com base no status
        if status_atual == "Ativo":
            expander_title = f"🔵 **Contrato Nº {contrato['numero_contrato']}** | Cliente: {cliente['nome_razao_social']}"
        elif status_atual == "Encerrado":
            expander_title = f"⚫ **Contrato Nº {contrato['numero_contrato']}** | Cliente: {cliente['nome_razao_social']}"
        else: # Encerrado com Pendências
            expander_title = f"🟠 **Contrato Nº {contrato['numero_contrato']}** | Cliente: {cliente['nome_razao_social']}"

        with st.expander(expander_title):
            st.markdown(f"**Status Atual:** `{status_atual}`")
            st.markdown(f"**Data de Geração:** {datetime.fromisoformat(contrato['data_geracao']).strftime('%d/%m/%Y')}")
            
            # (Aqui você pode adicionar o restante dos detalhes do contrato como antes)

            st.markdown("---")
            st.markdown("##### Ações do Contrato")
            
            botoes_col1, botoes_col2, botoes_col3, botoes_col4 = st.columns(4)
            
            with botoes_col1:
                # Botão de Download habilitado
                contrato_docx = utils.gerar_contrato_docx(contrato)
                st.download_button(
                    label="Baixar Novamente",
                    data=contrato_docx,
                    file_name=f"CONTRATO_{contrato['numero_contrato']}_{cliente['nome_razao_social']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_{contrato['id_contrato']}",
                    use_container_width=True
                )

            # Lógica para mostrar botões de mudança de status
            if status_atual == "Ativo":
                with botoes_col2:
                    if st.button("Encerrar Contrato", key=f"end_{contrato['id_contrato']}", use_container_width=True):
                        atualizar_status_contrato(drive, contrato['id_contrato'], "Encerrado")
                with botoes_col3:
                    if st.button("Encerrar com Pendências", key=f"pend_{contrato['id_contrato']}", use_container_width=True):
                        atualizar_status_contrato(drive, contrato['id_contrato'], "Encerrado com Pendências")
            else:
                with botoes_col2:
                    if st.button("Reativar Contrato", key=f"reactivate_{contrato['id_contrato']}", use_container_width=True):
                        atualizar_status_contrato(drive, contrato['id_contrato'], "Ativo")

            with botoes_col4:
                if st.button("Excluir", type="primary", key=f"delete_{contrato['id_contrato']}", use_container_width=True):
                    contratos_atualizados = [c for c in contratos_data if c['id_contrato'] != contrato['id_contrato']]
                    utils.write_data(contracts_file, contratos_atualizados)
                    st.success(f"Contrato Nº {contrato['numero_contrato']} foi excluído.")
                    st.rerun()

utils.exibir_rodape()
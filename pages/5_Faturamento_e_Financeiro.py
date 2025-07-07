# pages/5_Faturamento_e_Financeiro.py
import streamlit as st
import utils
import uuid
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Faturamento e Financeiro", layout="wide")

# --- Função de Ação para Atualizar Status ---
def atualizar_status_fatura(drive, invoices_file, faturas_data, id_fatura, novo_status):
    """Encontra uma fatura na lista, atualiza seu status e salva o arquivo de volta no Drive."""
    for fatura in faturas_data:
        if fatura['id_fatura'] == id_fatura:
            fatura['status'] = novo_status
            break
    utils.write_data(invoices_file, faturas_data)
    st.success(f"Status da fatura Nº {fatura['numero_fatura']} atualizado para '{novo_status}'.")
    st.rerun() # Recarrega a página para refletir a mudança

# --- Autenticação ---
if not st.session_state.get('autenticado'):
    st.error("Acesso negado. Por favor, realize o login.")
    st.stop()

with st.sidebar:
    st.success(f"Bem-vindo, {st.session_state.get('nome_usuario')}!")
    if st.button("Logout"):
        st.session_state.clear()
        st.switch_page("1_Login.py")

st.title("Faturamento e Gerenciamento Financeiro")

# --- Carregamento dos Dados ---
try:
    drive = utils.login_gdrive()
    contracts_file = utils.get_database_file(drive, "contracts.json")
    contratos_data = utils.read_data(contracts_file)
    invoices_file = utils.get_database_file(drive, "invoices.json")
    faturas_data = utils.read_data(invoices_file)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- Abas ---
tab1, tab2 = st.tabs([" Lançar Nova Fatura ", " Gerenciar Faturas Existentes "])

# --- Aba de Criação de Fatura ---
with tab1:
    st.header("Criar Nova Fatura")
    
    contratos_ativos = [c for c in contratos_data if c.get('status') == 'Ativo']
    if not contratos_ativos:
        st.warning("Não há contratos ativos para faturar.")
    else:
        # Cria uma lista de labels para o selectbox, combinando número e nome do cliente
        lista_contratos = {f"{c['numero_contrato']} - {c['cliente']['nome_razao_social']}": c['id_contrato'] for c in contratos_ativos}
        
        # Garante que o selectbox tem um valor selecionado por padrão se houver contratos
        contrato_selecionado_label = None
        if lista_contratos:
            contrato_selecionado_label = st.selectbox("Selecione um Contrato Ativo", options=list(lista_contratos.keys()))
        
        # Encontra o objeto do contrato selecionado
        contrato_obj = None
        if contrato_selecionado_label:
            id_contrato_selecionado = lista_contratos.get(contrato_selecionado_label)
            contrato_obj = next((c for c in contratos_ativos if c['id_contrato'] == id_contrato_selecionado), None)
            
        if contrato_obj: # Somente mostra o formulário se um contrato válido for selecionado
            st.info(f"Cliente: **{contrato_obj['cliente']['nome_razao_social']}** | Endereço da Obra: **{contrato_obj['endereco_obra']}**")

            with st.form("form_fatura"):
                vencimento = st.date_input("Data de Vencimento", value=date.today() + timedelta(days=7))
                descricao = st.text_area("Descrição dos Serviços/Produtos na Fatura", value=f"Referente a locação do contrato {contrato_obj['numero_contrato']}")
                valor = st.number_input("Valor Total da Fatura (R$)", min_value=0.01, format="%.2f")
                forma_pagamento = st.selectbox("Forma de Pagamento", ["BOLETO BANCÁRIO", "PIX", "TRANSFERÊNCIA"])
                
                # CORREÇÃO: Adicionando o valor padrão no text_area para Observações
                observacoes_padrao = "Esse recibo só tem validade mediante a quitação do boleto bancário."
                observacoes = st.text_area("Observações (opcional):", value=observacoes_padrao, height=70) # Usando text_area e definindo valor padrão

                submitted = st.form_submit_button("Gerar e Salvar Fatura")
                
                if submitted:
                    # Coleta informações adicionais do cliente para o template da fatura
                    # (já com os .get() para segurança em caso de dados faltando)
                    cliente_endereco = contrato_obj['cliente'].get('endereco', '')
                    cliente_bairro = contrato_obj['cliente'].get('bairro', '')
                    cliente_cidade = contrato_obj['cliente'].get('cidade', '')
                    cliente_estado = contrato_obj['cliente'].get('estado', 'SC') # Padrão SC se não houver
                    cliente_cep = contrato_obj['cliente'].get('cep', '')

                    novo_numero_fatura = utils.get_next_fatura_number(drive)
                    if novo_numero_fatura:
                        nova_fatura = {
                            "id_fatura": str(uuid.uuid4()),
                            "numero_fatura": novo_numero_fatura,
                            "id_contrato": id_contrato_selecionado,
                            "status": "Pendente",
                            "data_emissao": date.today().isoformat(),
                            "data_vencimento": vencimento.isoformat(),
                            "descricao_servico": descricao,
                            "valor_total": f"{valor:.2f}",
                            "forma_pagamento": forma_pagamento,
                            "observacao": observacoes,
                            "cliente_info": contrato_obj['cliente'],
                            "contrato_info": {"numero": contrato_obj['numero_contrato']}
                        }
                        faturas_data.append(nova_fatura)
                        utils.write_data(invoices_file, faturas_data)
                        
                        # Prepare os dados para o template DOCX
                        dados_template_para_docx = {
                            "NUMERO_FATURA": novo_numero_fatura, 
                            "DATA_EMISSAO": date.today().strftime('%d/%m/%Y'),
                            "NOME_CLIENTE": contrato_obj['cliente']['nome_razao_social'], 
                            "CNPJ_CLIENTE": contrato_obj['cliente']['cpf_cnpj'],
                            "ENDERECO_CLIENTE": cliente_endereco,
                            "BAIRRO_CLIENTE": cliente_bairro, # Passando para o .get() no utils.py
                            "CIDADE_CLIENTE": cliente_cidade, # Passando para o .get() no utils.py
                            "ESTADO_CLIENTE": cliente_estado,   # Passando para o .get() no utils.py
                            "CEP_CLIENTE": cliente_cep,         # Passando para o .get() no utils.py
                            "FORMA_PAGAMENTO": forma_pagamento, 
                            "DATA_VENCIMENTO": vencimento.strftime('%d/%m/%Y'),
                            "DESCRICAO_SERVICO": descricao, 
                            "VALOR_TOTAL": f"{valor:.2f}", 
                            "OBSERVACAO": observacoes # Este vem do text_area editável
                        }
                        st.session_state.documento_gerado = utils.gerar_fatura_docx(dados_template_para_docx)
                        st.session_state.nome_arquivo_doc = f"FATURA_{novo_numero_fatura}_{contrato_obj['cliente']['nome_razao_social']}.docx"
                        st.success("Fatura gerada e salva com sucesso!")

            if 'documento_gerado' in st.session_state:
                st.download_button(
                    "Baixar Fatura em Word (.docx)", 
                    data=st.session_state.documento_gerado, 
                    file_name=st.session_state.nome_arquivo_doc, 
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                del st.session_state['documento_gerado']

# --- Aba 2: Gerenciar Faturas Existentes ---
with tab2:
    st.header("Consultar e Gerenciar Faturas")
    
    status_opcoes = ["Todas", "Pendente", "Liquidada", "Cancelada"]
    status_selecionado = st.selectbox("Filtrar por Status", options=status_opcoes)
    
    faturas_filtradas = faturas_data
    if status_selecionado != "Todas":
        faturas_filtradas = [f for f in faturas_data if f.get('status') == status_selecionado]
        
    if not faturas_filtradas:
        st.info("Nenhuma fatura encontrada com os filtros atuais.")
    else:
        for f in sorted(faturas_filtradas, key=lambda i: i['data_emissao'], reverse=True):
            status = f.get('status', 'N/A')
            cor_status = {"Pendente": "🟠", "Liquidada": "🟢", "Cancelada": "⚫"}.get(status, "⚪")
            
            expander_title = (
                f"{cor_status} **Fatura Nº {f['numero_fatura']}** | "
                f"Cliente: **{f['cliente_info']['nome_razao_social']}** | "
                f"Venc: {datetime.fromisoformat(f['data_vencimento']).strftime('%d/%m/%Y')} | R$ {f['valor_total']}"
            )

            with st.expander(expander_title):
                st.markdown(f"**Status Atual:** `{status}`")
                st.markdown(f"**Contrato Associado:** {f['contrato_info']['numero']}")
                st.markdown(f"**Descrição:** {f['descricao_servico']}")
                
                st.markdown("---")
                st.markdown("##### Ações")
                
                cols_acoes = st.columns(4)
                
                with cols_acoes[0]:
                    # Ao baixar novamente, garanta que todos os dados do cliente são passados
                    # incluindo bairro, cidade, estado e CEP, para que o utils.py possa usá-los com .get()
                    fatura_info_para_download = {
                        "NUMERO_FATURA": f.get("numero_fatura"), 
                        "DATA_EMISSAO": datetime.fromisoformat(f.get("data_emissao")).strftime('%d/%m/%Y'),
                        "NOME_CLIENTE": f['cliente_info'].get('nome_razao_social', ''), 
                        "CNPJ_CLIENTE": f['cliente_info'].get('cpf_cnpj', ''),
                        "ENDERECO_CLIENTE": f['cliente_info'].get('endereco', ''),
                        "BAIRRO_CLIENTE": f['cliente_info'].get('bairro', ''),
                        "CIDADE_CLIENTE": f['cliente_info'].get('cidade', ''),
                        "ESTADO_CLIENTE": f['cliente_info'].get('estado', ''),
                        "CEP_CLIENTE": f['cliente_info'].get('cep', ''),
                        "FORMA_PAGAMENTO": f.get("forma_pagamento", ''), 
                        "DATA_VENCIMENTO": datetime.fromisoformat(f.get("data_vencimento")).strftime('%d/%m/%Y'),
                        "DESCRICAO_SERVICO": f.get("descricao_servico", ''), 
                        "VALOR_TOTAL": f.get("valor_total", ''), 
                        "OBSERVACAO": f.get("observacao", '') # Passa a observação existente
                    }
                    fatura_docx = utils.gerar_fatura_docx(fatura_info_para_download)
                    st.download_button("Baixar Novamente", data=fatura_docx, file_name=f"FATURA_{f['numero_fatura']}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"dl_{f['id_fatura']}")

                if status == "Pendente":
                    with cols_acoes[1]:
                        if st.button("Marcar como Liquidada", key=f"paid_{f['id_fatura']}", use_container_width=True):
                            atualizar_status_fatura(drive, invoices_file, faturas_data, f['id_fatura'], "Liquidada")
                    with cols_acoes[2]:
                        if st.button("Cancelar Fatura", type="primary", key=f"cancel_{f['id_fatura']}", use_container_width=True):
                            atualizar_status_fatura(drive, invoices_file, faturas_data, f['id_fatura'], "Cancelada")
                
                elif status in ["Liquidada", "Cancelada"]:
                    with cols_acoes[1]:
                        if st.button("Reverter para Pendente", key=f"revert_{f['id_fatura']}", use_container_width=True):
                            atualizar_status_fatura(drive, invoices_file, faturas_data, f['id_fatura'], "Pendente")

utils.exibir_rodape()
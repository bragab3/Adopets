# Ambiente das medições

Duas medições com o mesmo cenário de carga (rampa 1 → 10 → 50 → 100 VUs, sem tempo de espera, 390 s):

- **Medição 1** — 09/11/2026, sistema original.
- **Medição 2** — 15/11/2026, depois das otimizações (ver [RELATORIO.md](../../RELATORIO.md), seções 3.8 e 4.8).

---

# Medição 1 — 09/11/2026

## Servidor (Node + MySQL)
- Máquina: PC, CPU i5-13400, RAM 32GB, SO Windows
- Node: v24.22.0
- MySQL: 8.4.7, rodando local
- Pool de conexões do servidor: 10 
- Usuários no banco antes do teste: 3
- Variáveis do MySQL: valores padrão do 8.4 (`innodb_redo_log_capacity` = 100 MB, `innodb_buffer_pool_size` = 128 MB, `innodb_flush_log_at_trx_commit` = 1, `max_connections` = 151). *Padrões documentados: a consulta `SHOW VARIABLES` não foi guardada na época.*
- Horário (fuso −03:00): Login às 02:45, Cadastro às 02:58

## Gerador de carga (k6)
- Rodou na mesma máquina do servidor? sim
- Versão: k6.exe v2.3.0 (commit/e088784614, go1.26.8, windows/amd64)
- Rede: Ethernet

---

# Medição 2 — 15/11/2026

## Servidor (Node + MySQL)
- Máquina, Node e MySQL: os mesmos da Medição 1 (i5-13400, 32 GB, Windows, Node v24.22.0, MySQL 8.4.7 local)
- Servidor: `server.js` otimizado, com 1 processo Node
- Variáveis de ambiente (conforme o `B.arquivo.env`):

  | Variável | Valor | O que faz |
  |---|---:|---|
  | `DB_POOL_SIZE` | 10 | conexões do pool MySQL por processo |
  | `CLUSTER_WORKERS` | 1 | processos Node (1 = sem cluster) |
  | `DB_PREWARM` | 1 | abre as conexões do pool antes de aceitar requisições |
  | `DB_USE_EXECUTE` | 1 | consultas do login e do cadastro como prepared statements (`pool.execute`) |

- Variáveis do MySQL (aplicadas com `SET PERSIST`):

  | Variável | Antes (padrão 8.4) | Medição 2 |
  |---|---:|---:|
  | `innodb_redo_log_capacity` | 100 MB | 2 GB (2147483648) |
  | `innodb_buffer_pool_size` | 128 MB | 1 GB (1073741824) |
  | `innodb_flush_log_at_trx_commit` | 1 | 1 (não alterado) |
  | `max_connections` | 151 | 151 (não alterado) |

  O redimensionamento do buffer pool foi concluído em 15/11/2026 às 14:21 (`Innodb_buffer_pool_resize_status`).
- Horário (fuso −03:00): Login às 14:54 e Cadastro às 20:35 (início às 20:35:32). O Cadastro foi executado de novo; a execução das 15:02 foi substituída por esta.
- Usuários no banco antes do teste de Login: **não registrado**
- DELETE dos usuários de teste antes do Cadastro: **não registrado**

## Gerador de carga (k6)
- Rodou na mesma máquina do servidor? sim
- Versão: k6 v2.3.0, a mesma da Medição 1
- Rede: Ethernet

---

# Pendências de registro

Itens que os arquivos do projeto não permitem confirmar. Se você souber, corrija aqui e em [RELATORIO.md](../../RELATORIO.md) (seção 2.1):

1. Valores de `innodb_redo_log_capacity` e `innodb_buffer_pool_size` **antes** da alteração (aqui foram assumidos os padrões do 8.4).
2. Valores reais do `.env` usado na Medição 2 (aqui foram assumidos os do `B.arquivo.env`).
3. Se o `innodb_flush_log_at_trx_commit` foi mantido em 1.
4. Quantos usuários havia na tabela `usuario` antes do Login da Medição 2 e antes do Cadastro de 20:35, e se o `DELETE FROM usuario WHERE email LIKE 'user\_%@teste.com';` foi executado antes de cada execução do Cadastro (a execução das 15:02 inseriu ≈ 355.700 usuários).

5. Configuração do Cadastro de 20:35 (pool, variáveis `DB_*` do `.env` e variáveis do MySQL): foi **assumida igual** à da Medição 2 descrita acima. Se algo mudou, corrija aqui e na seção 2.1 do relatório.
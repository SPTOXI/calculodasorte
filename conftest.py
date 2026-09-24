import os

# Senha conhecida para o admin criado no banco de teste (em produção ela é aleatória)
os.environ.setdefault('ADMIN_INITIAL_PASSWORD', '123456')

# 📊 Guía de LangSmith para Dexter

## ¿Qué es LangSmith?

LangSmith es la plataforma oficial de observabilidad y debugging de LangChain/LangGraph. Te permite:

- **Tracing completo**: Ver cada paso del agente (planning, execution, validation, answer)
- **Debugging**: Identificar exactamente dónde fallan las chains/tools
- **Performance monitoring**: Medir latencias y costos de cada componente
- **Evaluación**: Comparar diferentes versiones del agente
- **Logs centralizados**: Todo en un solo lugar

## 🚀 Configuración

### 1. Obtén tu API Key

1. Ve a [smith.langchain.com](https://smith.langchain.com/)
2. Crea una cuenta o inicia sesión
3. Ve a Settings → API Keys
4. Crea un nuevo API key

### 2. Configura las Variables de Entorno

Edita tu archivo `.env`:

```bash
# LangSmith (opcional)
LANGSMITH_API_KEY=tu-api-key-aqui
LANGSMITH_PROJECT=dexter-project
LANGSMITH_TRACING=true
```

**Nota**: Si no configuras estas variables, Dexter funcionará normalmente sin tracing.

### 3. Instala las Dependencias

```bash
uv sync
```

## 📈 Uso

### Desde el CLI

Simplemente ejecuta Dexter normalmente:

```bash
# Con versión default
uv run dexter-agent

# Con LangGraph
uv run dexter-agent --use-graph
```

Si LangSmith está configurado, verás este mensaje al inicio:

```Output
📊 LangSmith tracing enabled: Project 'dexter-project'
   View traces at: https://smith.langchain.com/o/default/projects/p/dexter-project
```

### Caso 3: Comparar Versiones

Para comparar `agent.py` vs `agent_graph.py`:

1. Crea dos proyectos en LangSmith:
   - `dexter-chains`
   - `dexter-graph`

2. Ejecuta la misma query en ambas versiones:

```bash
# Versión chains
LANGSMITH_PROJECT=dexter-chains uv run dexter-agent
>> What is the price of Apple?

# Versión graph
LANGSMITH_PROJECT=dexter-graph uv run dexter-agent --use-graph
>> What is the price of Apple?
```

## 📚 Recursos

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangSmith Pricing](https://www.langchain.com/pricing)
- [LangChain Tracing Guide](https://python.langchain.com/docs/langsmith/walkthrough)

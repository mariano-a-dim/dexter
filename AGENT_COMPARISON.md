# Comparación: Agent vs AgentGraph

Este documento explica las diferencias entre las dos implementaciones del agente disponibles en Dexter.

## 📁 Archivos

- **`agent.py`**: Implementación original usando LangChain chains
- **`agent_graph.py`**: Nueva implementación usando LangGraph

## 🔄 Diferencias Clave

### agent.py (LangChain Chains)

**Ventajas:**

- ✅ Código más simple y directo
- ✅ Menos abstracciones

**Limitaciones:**

- ⚠️ Control de flujo menos explícito
- ⚠️ Difícil agregar ciclos de retry o re-planning
- ⚠️ Estado implícito (variables en memoria)
- ⚠️ Menos escalable para flujos complejos

**Arquitectura:**

```
Query → Planning Chain → [Task Loop] → Answer Chain
                             ↓
                      Executor → Validator
```

### agent_graph.py (LangGraph)

**Ventajas:**

- ✅ **Control de flujo explícito**: Nodos y edges claramente definidos
- ✅ **Estado compartido**: TypedDict con toda la información
- ✅ **Fácil de extender**: Agregar nodos (ej: error_handler, replanner) es trivial
- ✅ **Visualizable**: Puedes exportar el grafo como diagrama
- ✅ **Ciclos controlados**: Retry logic, replanning, loops condicionales
- ✅ **Better debugging**: Puedes inspeccionar el estado en cada nodo
- ✅ **Paralelización**: Potencial para ejecutar nodos en paralelo

**Arquitectura:**

```
                    ┌─────────┐
                    │ Planner │
                    └────┬────┘
                         │
                    ┌────▼────┐
            ┌───────┤ Router  ├───────┐
            │       └─────────┘       │
            │                         │
    ┌───────▼────────┐         ┌─────▼────┐
    │    Executor    │         │ Answerer │
    └───────┬────────┘         └─────┬────┘
            │                         │
    ┌───────▼────────┐                │
    │   Validator    │                │
    └───────┬────────┘                │
            │                         │
            └────┬────────────────────┘
                 │
              ┌──▼──┐
              │ END │
              └─────┘
```

## 🚀 Uso

Ambas versiones tienen **la misma API**:

```python
from dexter.agent import Agent
from dexter.agent_graph import AgentGraph

# Versión langchain
agent = Agent(max_steps=20, max_steps_per_task=3)
answer = agent.run("consulta")

# Versión LangGraph
agent = AgentGraph(max_steps=20, max_steps_per_task=3)
answer = agent.run("consulta")
```

## 📊 Estado del Grafo (AgentGraph)

El estado se maneja explícitamente en `AgentGraphState`:

```python
class AgentGraphState(TypedDict):
    query: str                    # Query original del usuario
    tasks: List[Task]             # Lista de tareas planificadas
    current_task_idx: int         # Índice de tarea actual
    session_outputs: List[str]    # Outputs acumulados de herramientas
    answer: str                   # Respuesta final
    current_task_result: dict     # Resultado de tarea actual
```

## 📦 Instalación

Asegúrate de tener `langgraph` instalado:

```bash
uv pip install -e .
```

## 🎓 Recursos

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Tutorials](https://langchain-ai.github.io/langgraph/tutorials/)

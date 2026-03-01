import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.models.log_analysis import LogWatcher, LogTemplate

async def ask_about_logs(db: AsyncSession, watcher: LogWatcher, question: str, hours: int = 24) -> str:
    # 1. 查询过去N小时更新过/命中过的模板
    time_limit = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # 优化：最多取 Top 100 高频模板避免上下文超限
    rows = await db.execute(
        select(LogTemplate)
        .where(
            LogTemplate.watcher_id == watcher.id,
            LogTemplate.last_seen_at >= time_limit
        )
        .order_by(LogTemplate.hit_count.desc())
        .limit(100)
    )
    templates = rows.scalars().all()
    
    if not templates:
        return f"过去 {hours} 小时内没有收集到任何关于 '{watcher.name}' 的新日志数据。"
        
    # 2. 格式化日志模板为上下文
    context_lines = []
    for t in templates:
        raw_samples = t.sample_logs
        samples = raw_samples if isinstance(raw_samples, list) else []
        # 为了节约 Token，最多带两条最新样本
        sample_str = "\n    ".join([str(x) for x in samples[:2]])
        context_lines.append(
            f"- [Cluster {t.cluster_id}] (出现次数: {t.hit_count}, 最后出现: {t.last_seen_at.strftime('%Y-%m-%d %H:%M:%S')})\n"
            f"  模板: {t.template_str}\n"
            f"  样本: {sample_str}"
        )
    
    context_text = "\n\n".join(context_lines)
    
    # 3. 调用大语言模型进行问答
    try:
        # 这里兼容原来根目录下的 main.py 中用户配置的支持
        model_name = os.getenv("LLM_MODEL", "glm-4") if os.getenv("ZHIPU_API_KEY") else os.getenv("LLM_MODEL", "gpt-4o")
        # 由于用户在根目录的main.py写了gpt-5.2和https://api.codexzh.com/v1这里我们兼容它
        api_base = os.getenv("OPENAI_API_BASE", "https://api.codexzh.com/v1") 
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return "提示：服务端缺少 OPENAI_API_KEY 配置，无法调用大模型 API 分析日志。"
            
        llm = ChatOpenAI(
            temperature=0.1,
            model=os.getenv("LLM_MODEL", "gpt-5.2"),
            openai_api_key=api_key,
            openai_api_base=api_base
        )
        
        system_prompt = (
            "你是一个高级的 DevOps 智能监控与日志分析助手。\n"
            "用户向系统配置了基于 drain3 算法聚合的日志流监控。\n"
            "下面是经过日志解析与聚类引擎发现的日志模板(Cluster)数据。\n"
            "每一条日志模板内容中的 `<*>` 代表被泛化掉的动态变量（如时间戳、IP、UUID、具体的错误指针等），\n"
            "系统还会提供最原始的样例(样本)以供你推测该类日志的具体用途。\n\n"
            "请根据上下文提供的数据，准确、专业地回答用户的问题。\n"
            "请注意查阅各个日志的 `出现次数` 以及是否符合用户的筛选条件。\n"
            "如果在数据中没有找到能回答用户问题的信息，请如实告知“并没有发现相关的 timeout 或 outofmemory 的迹象”等，不要编造未发生的告警。"
        )
        
        user_prompt = f"以下是监控任务 '{watcher.name}' 过去 {hours} 小时内的日志提取摘要：\n\n{context_text}\n\n我的提问是：{question}"
        
        # 调试输出（可选）
        print(f"--- Sending LLM Request Context (Len: {len(user_prompt)}) ---")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"AI 分析调用过程中出现异常：{str(e)}"

"""
Word Discovery Logic Module
詞彙發現的核心邏輯，從 DAG 中提取出來便於測試和維護
"""

from typing import List, Dict, Set, Tuple


def filter_and_validate_words(
    gemini_replace_words: List[Dict],
    gemini_special_words: List[Dict],
    existing_replace_mapping: Dict[str, str],
    existing_special_words: Set[str]
) -> Tuple[List[Dict], List[Dict]]:
    """
    過濾和驗證 Gemini 發現的詞彙

    規則：
    1. Protected Words 自動顛倒：如果 source 在 protected_words 中，顛倒 source 和 target
    2. Source 已存在自動轉換：DB: A->B, Gemini: A->C  =>  C->B
    3. 跳過重複的 source：轉換後的 source 如果已存在，跳過
    4. Target 自動加入 special words：替換詞彙的 target 自動加入特殊詞彙（如果不在 DB）
    5. 跳過已存在的 special words

    參數:
        gemini_replace_words: Gemini 建議的替換詞彙列表
        gemini_special_words: Gemini 建議的特殊詞彙列表
        existing_replace_mapping: 現有的替換映射 {source: target}
        existing_special_words: 現有的特殊詞彙集合

    返回:
        (filtered_replace, filtered_special): 過濾後的替換詞彙和特殊詞彙列表
    """
    # 計算衍生集合
    replace_sources_set = set(existing_replace_mapping.keys())
    replace_targets_set = set(existing_replace_mapping.values())
    protected_words_set = replace_targets_set | existing_special_words

    # 過濾替換詞彙
    filtered_replace = []
    auto_add_special = []

    for item in gemini_replace_words:
        source = item['source']
        target = item['target']

        # 基礎規則: 如果 source 和 target 相同，則跳過
        if source == target:
            item['_skip_reason'] = f'source and target are the same: {source}'
            continue

        original_source = source
        original_target = target

        # 規則 1: Protected Words 自動顛倒
        # source 不可以是 protected words（已確認的標準詞）
        if source in protected_words_set:
            source, target = target, source
            item['source'] = source
            item['target'] = target
            item['_transformation'] = f'swapped (protected): {original_source} <-> {original_target}'

            # Swap 後檢查是否完全重複（source -> target 的組合已存在）
            if source in replace_sources_set and existing_replace_mapping[source] == target:
                item['_skip_reason'] = f'duplicate after swap: {source} -> {target}'
                continue

        # 規則 2: Source 已存在自動轉換
        # DB: A->B, Gemini: A->C  =>  C->B
        if source in replace_sources_set:
            db_target = existing_replace_mapping[source]
            new_source = target
            new_target = db_target

            item['source'] = new_source
            item['target'] = new_target
            item['_transformation'] = f'transformed: {original_source}->{original_target} => {new_source}->{new_target}'

            source = new_source
            target = new_target

            # 規則 3: 檢查轉換後的 source 是否已經存在
            if source in replace_sources_set:
                item['_skip_reason'] = f'transformed source already exists: {source}'
                continue

        # 通過所有檢查，加入過濾後的列表
        filtered_replace.append(item)

        # 規則 4: Target 自動加入 special words（如果不在 DB 中）
        if target not in existing_special_words:
            auto_add_special.append({
                'word': target,
                'type': 'auto_from_replace',
                'confidence': 1.0,
                'examples': [f'替換詞彙的目標：{source} -> {target}'],
                'reason': f'自動從替換詞彙的目標詞彙加入',
                '_auto_added': True
            })
            # 更新集合，避免重複加入
            existing_special_words.add(target)

    # 過濾特殊詞彙
    filtered_special = []

    for item in gemini_special_words:
        word = item['word']

        # 規則 5: 跳過已存在的 special words
        if word in existing_special_words:
            item['_skip_reason'] = f'already exists in special_words: {word}'
            continue

        filtered_special.append(item)

    # 合併自動加入的 special words
    all_special = filtered_special + auto_add_special

    return filtered_replace, all_special


def format_transformation_summary(filtered_replace: List[Dict], filtered_special: List[Dict]) -> str:
    """
    格式化轉換摘要，便於查看處理結果

    參數:
        filtered_replace: 過濾後的替換詞彙
        filtered_special: 過濾後的特殊詞彙

    返回:
        格式化的摘要字串
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Word Discovery Transformation Summary")
    lines.append("=" * 60)

    # Replace words
    lines.append(f"\n替換詞彙 ({len(filtered_replace)} 個):")
    for item in filtered_replace:
        transformation = item.get('_transformation', '')
        if transformation:
            lines.append(f"  ✓ {item['source']} -> {item['target']}")
            lines.append(f"    轉換: {transformation}")
        else:
            lines.append(f"  ✓ {item['source']} -> {item['target']}")

    # Special words
    auto_count = sum(1 for item in filtered_special if item.get('_auto_added', False))
    manual_count = len(filtered_special) - auto_count

    lines.append(f"\n特殊詞彙 ({len(filtered_special)} 個, 手動: {manual_count}, 自動: {auto_count}):")
    for item in filtered_special:
        if item.get('_auto_added'):
            lines.append(f"  ✓ {item['word']} (自動從替換詞彙加入)")
        else:
            lines.append(f"  ✓ {item['word']} (類型: {item.get('type', 'unknown')})")

    lines.append("=" * 60)

    return "\n".join(lines)

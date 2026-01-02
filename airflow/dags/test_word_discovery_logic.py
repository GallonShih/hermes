"""
Word Discovery Logic Tests
測試詞彙發現的核心邏輯
"""

import sys
from word_discovery_logic import filter_and_validate_words, format_transformation_summary


def run_test_case(name: str, test_func):
    """執行單個測試案例"""
    print(f"\n{'='*60}")
    print(f"測試案例: {name}")
    print('='*60)
    try:
        test_func()
        print(f"✅ 測試通過: {name}")
        return True
    except AssertionError as e:
        print(f"❌ 測試失敗: {name}")
        print(f"   錯誤: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 測試錯誤: {name}")
        print(f"   異常: {str(e)}")
        return False


def test_case_1_protected_word_swap():
    """
    測試案例 1: Protected Words 自動顛倒

    情境: AI 錯誤地建議將標準詞替換為錯字
    DB: special_words = {"甄嬛"}
    Gemini: "甄嬛" -> "甄環"
    預期: 自動顛倒為 "甄環" -> "甄嬛"
    """
    gemini_replace = [
        {'source': '甄嬛', 'target': '甄環', 'confidence': 0.9}
    ]
    gemini_special = []
    existing_replace = {}
    existing_special = {'甄嬛'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_replace) == 1, f"應該有 1 個替換詞彙，實際: {len(filtered_replace)}"
    assert filtered_replace[0]['source'] == '甄環', f"source 應該是 '甄環'，實際: {filtered_replace[0]['source']}"
    assert filtered_replace[0]['target'] == '甄嬛', f"target 應該是 '甄嬛'，實際: {filtered_replace[0]['target']}"
    assert '_transformation' in filtered_replace[0], "應該有轉換記錄"

    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_2_source_exists_transform():
    """
    測試案例 2: Source 已存在自動轉換

    情境: AI 發現已知變體的新變體
    DB: "隨風搖GG" -> "隨風搖雞雞"
    Gemini: "隨風搖GG" -> "隨風搖ㄐㄐ"
    預期: 轉換為 "隨風搖ㄐㄐ" -> "隨風搖雞雞"
    """
    gemini_replace = [
        {'source': '隨風搖GG', 'target': '隨風搖ㄐㄐ', 'confidence': 0.95}
    ]
    gemini_special = []
    existing_replace = {'隨風搖GG': '隨風搖雞雞'}
    existing_special = {'隨風搖雞雞'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_replace) == 1, f"應該有 1 個替換詞彙，實際: {len(filtered_replace)}"
    assert filtered_replace[0]['source'] == '隨風搖ㄐㄐ', f"source 應該是 '隨風搖ㄐㄐ'，實際: {filtered_replace[0]['source']}"
    assert filtered_replace[0]['target'] == '隨風搖雞雞', f"target 應該是 '隨風搖雞雞'，實際: {filtered_replace[0]['target']}"

    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_3_skip_transformed_duplicate():
    """
    測試案例 3: 跳過轉換後重複的 source

    情境: 轉換後的 source 已經存在於 DB 中
    DB: "10初" -> "10粗", "10初初" -> "10粗"
    Gemini: "10初" -> "10初初"
    預期: 轉換為 "10初初" -> "10粗"，但因為 "10初初" 已存在而跳過
    """
    gemini_replace = [
        {'source': '10初', 'target': '10初初', 'confidence': 0.85}
    ]
    gemini_special = []
    existing_replace = {
        '10初': '10粗',
        '10初初': '10粗'
    }
    existing_special = {'10粗'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_replace) == 0, f"應該跳過（轉換後重複），實際有 {len(filtered_replace)} 個"

    print("✓ 正確跳過轉換後重複的 source")
    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_4_auto_add_target_to_special():
    """
    測試案例 4: Target 自動加入 Special Words

    情境: 替換詞彙的 target 不在 special_words 中，應自動加入
    DB: special_words = {}
    Gemini: "眉姊姊" -> "眉姐姐"
    預期: 替換詞彙通過，且 "眉姐姐" 自動加入 special_words
    """
    gemini_replace = [
        {'source': '眉姊姊', 'target': '眉姐姐', 'confidence': 0.9}
    ]
    gemini_special = []
    existing_replace = {}
    existing_special = set()

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_replace) == 1, f"應該有 1 個替換詞彙，實際: {len(filtered_replace)}"
    assert len(filtered_special) == 1, f"應該有 1 個特殊詞彙（自動加入），實際: {len(filtered_special)}"
    assert filtered_special[0]['word'] == '眉姐姐', f"自動加入的詞應該是 '眉姐姐'，實際: {filtered_special[0]['word']}"
    assert filtered_special[0].get('_auto_added') == True, "應該標記為自動加入"

    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_5_skip_existing_special():
    """
    測試案例 5: 跳過已存在的 Special Words

    情境: AI 建議的特殊詞彙已經在 DB 中
    DB: special_words = {"果郡王", "華妃"}
    Gemini: special_words = ["果郡王", "敬嬪"]
    預期: 只加入 "敬嬪"，跳過 "果郡王"
    """
    gemini_replace = []
    gemini_special = [
        {'word': '果郡王', 'type': 'character', 'confidence': 0.95},
        {'word': '敬嬪', 'type': 'character', 'confidence': 0.92}
    ]
    existing_replace = {}
    existing_special = {'果郡王', '華妃'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_special) == 1, f"應該只有 1 個新特殊詞彙，實際: {len(filtered_special)}"
    assert filtered_special[0]['word'] == '敬嬪', f"詞彙應該是 '敬嬪'，實際: {filtered_special[0]['word']}"

    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_6_complex_scenario():
    """
    測試案例 6: 複雜綜合情境

    同時測試多個規則的組合應用
    """
    gemini_replace = [
        # 規則 1: Protected word swap
        {'source': '甄嬛', 'target': '甄環', 'confidence': 0.9},
        # 規則 2: Source exists transform
        {'source': '隨風搖GG', 'target': '隨風搖jj', 'confidence': 0.95},
        # 正常新增
        {'source': '此招雖險，勝算卻大', 'target': '此招雖險勝算卻大', 'confidence': 0.88},
    ]
    gemini_special = [
        # 規則 5: Skip existing
        {'word': '果郡王', 'type': 'character', 'confidence': 0.95},
        # 正常新增
        {'word': '寧嬪', 'type': 'character', 'confidence': 0.90},
    ]
    existing_replace = {
        '隨風搖GG': '隨風搖雞雞'
    }
    existing_special = {'甄嬛', '果郡王', '隨風搖雞雞'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證替換詞彙
    assert len(filtered_replace) == 3, f"應該有 3 個替換詞彙，實際: {len(filtered_replace)}"

    # 驗證第一個（swapped）
    assert filtered_replace[0]['source'] == '甄環'
    assert filtered_replace[0]['target'] == '甄嬛'

    # 驗證第二個（transformed）
    assert filtered_replace[1]['source'] == '隨風搖jj'
    assert filtered_replace[1]['target'] == '隨風搖雞雞'

    # 驗證第三個（normal）
    assert filtered_replace[2]['source'] == '此招雖險，勝算卻大'
    assert filtered_replace[2]['target'] == '此招雖險勝算卻大'

    # 驗證特殊詞彙（1 個 skip，1 個 manual，3 個 auto）
    # auto: 甄嬛, 隨風搖雞雞 (已存在不重複加), 此招雖險勝算卻大
    # manual: 寧嬪
    # total = 1 manual + 2 auto (甄嬛已存在, 隨風搖雞雞已存在, 只有此招雖險勝算卻大是新的) = 2
    assert len(filtered_special) >= 2, f"應該至少有 2 個特殊詞彙，實際: {len(filtered_special)}"

    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_7_chain_transformation():
    """
    測試案例 7: 鏈式轉換

    情境: Protected word + Source exists 同時觸發
    DB: "眉姐姐" in special_words, "眉姊姊" -> "眉姐姐"
    Gemini: "眉姐姐" -> "眉姊姊"
    預期: 先 swap -> "眉姊姊" -> "眉姐姐"，然後 transform -> skip（已存在）
    """
    gemini_replace = [
        {'source': '眉姐姐', 'target': '眉姊姊', 'confidence': 0.9}
    ]
    gemini_special = []
    existing_replace = {'眉姊姊': '眉姐姐'}
    existing_special = {'眉姐姐'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證：應該被跳過（swap 後變成 "眉姊姊" -> "眉姐姐"，但 "眉姊姊" 已存在）
    assert len(filtered_replace) == 0, f"應該跳過（鏈式轉換後重複），實際有 {len(filtered_replace)} 個"

    print("✓ 正確處理鏈式轉換情境")
    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_8_target_already_in_special():
    """
    測試案例 8: Target 已經在 Special Words 中

    情境: 替換詞彙的 target 已經在 special_words，不應重複加入
    DB: special_words = {"甄嬛"}
    Gemini: "甄環" -> "甄嬛"
    預期: 替換詞彙通過，但不重複加入 special_words
    """
    gemini_replace = [
        {'source': '甄環', 'target': '甄嬛', 'confidence': 0.95}
    ]
    gemini_special = []
    existing_replace = {}
    existing_special = {'甄嬛'}

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_replace) == 1, f"應該有 1 個替換詞彙，實際: {len(filtered_replace)}"
    assert len(filtered_special) == 0, f"不應該重複加入 special_words，實際有 {len(filtered_special)} 個"

    print(format_transformation_summary(filtered_replace, filtered_special))


def test_case_9_skip_same_source_target():
    """
    測試案例 9: 如果 source 和 target 相同，就直接 skip

    情境: Gemini 建議將某個詞替換為它自己（無意義建議）
    Gemini: "甄嬛" -> "甄嬛"
    預期: 直接跳過，不應出現在 filtered_replace 中
    """
    gemini_replace = [
        {'source': '甄嬛', 'target': '甄嬛', 'confidence': 0.99}
    ]
    gemini_special = []
    existing_replace = {}
    existing_special = set()

    filtered_replace, filtered_special = filter_and_validate_words(
        gemini_replace, gemini_special, existing_replace, existing_special
    )

    # 驗證
    assert len(filtered_replace) == 0, f"應該跳過（相同詞彙），實際有 {len(filtered_replace)} 個"

    print("✓ 正確跳過 source 和 target 相同的情境")
    print(format_transformation_summary(filtered_replace, filtered_special))


def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("開始執行 Word Discovery Logic 測試")
    print("="*60)

    test_cases = [
        ("Protected Words 自動顛倒", test_case_1_protected_word_swap),
        ("Source 已存在自動轉換", test_case_2_source_exists_transform),
        ("跳過轉換後重複的 Source", test_case_3_skip_transformed_duplicate),
        ("Target 自動加入 Special Words", test_case_4_auto_add_target_to_special),
        ("跳過已存在的 Special Words", test_case_5_skip_existing_special),
        ("複雜綜合情境", test_case_6_complex_scenario),
        ("鏈式轉換", test_case_7_chain_transformation),
        ("Target 已在 Special Words", test_case_8_target_already_in_special),
        ("跳過相同 Source 和 Target", test_case_9_skip_same_source_target),
    ]

    results = []
    for name, test_func in test_cases:
        results.append(run_test_case(name, test_func))

    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"通過: {passed}/{total}")
    print(f"失敗: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n❌ 有 {total - passed} 個測試失敗")
        return 1


if __name__ == '__main__':
    sys.exit(main())

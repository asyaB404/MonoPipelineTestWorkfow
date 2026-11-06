IMAGE_ANALYSIS_SCHEMA = {
    "image_id": "IMG-001",
    "image_stable_id": "IMG-BBBC9A1D",
    "image_type": "ui_mockup | flow_chart | state_chart | table_screenshot | decorative | unknown",
    "ocr_texts": [
        {
            "text_id": "TXT-001",
            "stable_text_id": "TXT-BBBC9A1D-001",
            "text": "购买",
            "role": "button_text | title | label | value | error_message | unknown",
        }
    ],
    "elements": [
        {
            "element_id": "ELE-001",
            "stable_element_id": "ELE-BBBC9A1D-001",
            "type": "button | input | text | list | popup | tab | icon | image | unknown",
            "name": "购买按钮",
            "visible_text": "购买",
            "state": "normal | disabled | selected | loading | error | unknown",
            "location": "界面右下角",
            "possible_action": "click | input | switch | scroll | close | none | unknown",
            "confidence": "high | medium | low",
        }
    ],
    "inferred_interactions": [
        {
            "interaction_id": "INT-001",
            "action": "点击购买按钮",
            "expected": "进入购买确认或触发购买流程",
            "basis_alias": ["IMG-001", "ELE-001", "TXT-001"],
            "basis_stable": ["IMG-BBBC9A1D", "ELE-BBBC9A1D-001", "TXT-BBBC9A1D-001"],
            "needs_confirmation": False,
        }
    ],
    "risks": [
        {
            "risk_id": "RISK-001",
            "description": "图片显示购买按钮，但正文未说明点击后的业务规则",
            "basis_alias": ["IMG-001", "ELE-001"],
            "basis_stable": ["IMG-BBBC9A1D", "ELE-BBBC9A1D-001"],
            "needs_confirmation": True,
        }
    ],
}


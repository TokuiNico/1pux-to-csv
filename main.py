#!/usr/bin/env python3
"""
1PUX to Apple CSV Converter

將 1Password 的 1PUX 格式轉換為 Apple CSV 格式
"""

import argparse
import csv
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def extract_export_data(one_pux_path: Path) -> Dict[str, Any]:
    """從 1PUX ZIP 檔案中提取 export.data JSON 資料"""
    if not one_pux_path.exists():
        raise FileNotFoundError(f"找不到檔案: {one_pux_path}")

    with zipfile.ZipFile(one_pux_path, 'r') as zip_file:
        # 尋找 export.data 檔案
        export_data_path = None
        for name in zip_file.namelist():
            if name.endswith('export.data') or name == 'export.data':
                export_data_path = name
                break

        if not export_data_path:
            raise ValueError("在 1PUX 檔案中找不到 export.data")

        # 讀取並解析 JSON
        with zip_file.open(export_data_path) as f:
            return json.load(f)


def extract_username(login_fields: List[Dict[str, Any]]) -> Optional[str]:
    """從 loginFields 中提取 username"""
    for field in login_fields:
        if field.get('designation') == 'username':
            return field.get('value', '')
    return None


def extract_password(login_fields: List[Dict[str, Any]]) -> Optional[str]:
    """從 loginFields 中提取 password"""
    for field in login_fields:
        if field.get('designation') == 'password':
            return field.get('value', '')
    return None


def extract_otp_auth(sections: List[Dict[str, Any]]) -> Optional[str]:
    """從 sections 中提取 OTP Auth"""
    for section in sections:
        fields = section.get('fields', [])
        for field in fields:
            field_id = field.get('id', '')
            if field_id.startswith('TOTP_'):
                value = field.get('value', {})
                if isinstance(value, dict):
                    totp = value.get('totp', '')
                    if totp:
                        return totp
                elif isinstance(value, str):
                    return value
    return None


def extract_url(overview: Dict[str, Any]) -> Optional[str]:
    """從 overview 中提取 URL"""
    # 優先使用 overview.url
    url = overview.get('url')
    if url:
        return url

    # 否則使用 urls 陣列的第一個
    urls = overview.get('urls', [])
    if urls and len(urls) > 0:
        return urls[0].get('url', '')

    return None


def format_field_value(field_value: Any) -> Optional[str]:
    """格式化不同類型的欄位值為可讀字串"""
    if not field_value:
        return None

    # 字串類型直接返回
    if isinstance(field_value, str):
        return field_value

    # 字典類型需要根據不同類型處理
    if isinstance(field_value, dict):
        # concealed 類型
        if 'concealed' in field_value:
            return field_value['concealed']

        # string 類型
        if 'string' in field_value:
            return field_value['string']

        # ssoLogin 類型：只需要 provider
        if 'ssoLogin' in field_value:
            sso_login = field_value['ssoLogin']
            if isinstance(sso_login, dict):
                provider = sso_login.get('provider', '')
                return provider if provider else None
            return None

        # menu 類型：選單選項
        if 'menu' in field_value:
            menu_value = field_value['menu']
            return menu_value if menu_value else None

        # address 類型：格式化地址
        if 'address' in field_value:
            addr = field_value['address']
            if isinstance(addr, dict):
                parts = []
                if addr.get('street'):
                    parts.append(addr['street'])
                city = addr.get('city', '')
                state = addr.get('state', '')
                zip_code = addr.get('zip', '')
                country = addr.get('country', '')

                # 組合城市、州、郵遞區號
                city_parts = [p for p in [city, state, zip_code] if p]
                if city_parts:
                    parts.append(', '.join(city_parts))

                if country:
                    parts.append(country)

                return ', '.join(parts) if parts else None

        # 其他未知類型，嘗試取得第一個值或轉為字串
        # 優先尋找常見的單一值鍵
        for key in ['value', 'text', 'name', 'label']:
            if key in field_value:
                val = field_value[key]
                if val:
                    return str(val)

        # 如果都沒有，返回 None（不輸出 JSON 結構）
        return None

    # 其他類型轉為字串
    return str(field_value)


def build_notes(details: Dict[str, Any], overview: Dict[str, Any]) -> str:
    """建立 Notes 欄位，合併各種資訊"""
    notes_parts = []

    # 1. notesPlain
    notes_plain = details.get('notesPlain', '')
    if notes_plain:
        notes_parts.append(notes_plain.strip())

    # 2. Tags
    tags = overview.get('tags', [])
    if tags:
        tags_str = ', '.join(tags)
        notes_parts.append(f"標籤: {tags_str}")

    # 3. 其他 loginFields（非 username/password）
    login_fields = details.get('loginFields', [])
    other_fields = []
    for field in login_fields:
        designation = field.get('designation', '')
        if designation not in ('username', 'password'):
            field_name = field.get('name', '')
            field_value = field.get('value', '')
            if field_value:
                if field_name:
                    other_fields.append(f"{field_name}: {field_value}")
                else:
                    other_fields.append(field_value)

    if other_fields:
        notes_parts.append("其他欄位:\n" + "\n".join(f"  - {f}" for f in other_fields))

    # 4. Sections 欄位（除了 OTP）
    sections = details.get('sections', [])
    section_fields = []
    for section in sections:
        section_title = section.get('title', '')
        fields = section.get('fields', [])
        for field in fields:
            field_id = field.get('id', '')
            # 跳過 OTP 欄位（已經在 OTPAuth 欄位中）
            if field_id.startswith('TOTP_'):
                continue

            field_title = field.get('title', '')
            field_value = field.get('value', '')

            # 使用格式化函數處理不同類型的 value
            formatted_value = format_field_value(field_value)

            if formatted_value:
                if section_title and field_title:
                    section_fields.append(f"{section_title} - {field_title}: {formatted_value}")
                elif field_title:
                    section_fields.append(f"{field_title}: {formatted_value}")
                else:
                    section_fields.append(formatted_value)

    if section_fields:
        notes_parts.append("額外資訊:\n" + "\n".join(f"  - {f}" for f in section_fields))

    # 5. 其他 URLs
    urls = overview.get('urls', [])
    if len(urls) > 1:
        other_urls = []
        for url_obj in urls[1:]:  # 跳過第一個（已經在 URL 欄位）
            url_str = url_obj.get('url', '')
            label = url_obj.get('label', '')
            if url_str:
                if label:
                    other_urls.append(f"{label}: {url_str}")
                else:
                    other_urls.append(url_str)
        if other_urls:
            notes_parts.append("其他網址:\n" + "\n".join(f"  - {u}" for u in other_urls))

    # 6. Password History
    password_history = details.get('passwordHistory', [])
    if password_history:
        notes_parts.append(f"密碼歷史記錄: {len(password_history)} 筆")

    return "\n---\n".join(notes_parts)


def convert_item_to_csv_row(item: Dict[str, Any]) -> Dict[str, str]:
    """將 1PUX item 轉換為 CSV 行"""
    overview = item.get('overview', {})
    details = item.get('details', {})

    # 提取各欄位
    title = overview.get('title', '')
    url = extract_url(overview) or ''

    login_fields = details.get('loginFields', [])
    username = extract_username(login_fields) or ''
    password = extract_password(login_fields) or ''

    sections = details.get('sections', [])
    otp_auth = extract_otp_auth(sections) or ''

    notes = build_notes(details, overview)

    return {
        'Title': title,
        'URL': url,
        'Username': username,
        'Password': password,
        'Notes': notes,
        'OTPAuth': otp_auth,
    }


def convert_1pux_to_csv(one_pux_path: Path, output_path: Path, include_archived: bool = False):
    """將 1PUX 檔案轉換為 Apple CSV 格式"""
    # 讀取 export.data
    data = extract_export_data(one_pux_path)

    # 提取所有 items
    csv_rows = []
    accounts = data.get('accounts', [])

    for account in accounts:
        vaults = account.get('vaults', [])
        for vault in vaults:
            items = vault.get('items', [])
            for item in items:
                # 檢查是否要包含 archived items
                state = item.get('state', 'active')
                if not include_archived and state == 'archived':
                    continue

                csv_row = convert_item_to_csv_row(item)
                csv_rows.append(csv_row)

    # 寫入 CSV（使用 UTF-8 with BOM 以確保 Excel 正確顯示）
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['Title', 'URL', 'Username', 'Password', 'Notes', 'OTPAuth']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"成功轉換 {len(csv_rows)} 筆記錄到 {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='將 1Password 1PUX 格式轉換為 Apple CSV 格式'
    )
    parser.add_argument(
        'input',
        type=Path,
        help='輸入的 1PUX 檔案路徑'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='輸出的 CSV 檔案路徑（預設為輸入檔名 + .csv）'
    )
    parser.add_argument(
        '--include-archived',
        action='store_true',
        help='包含已歸檔的項目'
    )

    args = parser.parse_args()

    # 確定輸出路徑
    if args.output:
        output_path = args.output
    else:
        output_path = args.input.with_suffix('.csv')

    try:
        convert_1pux_to_csv(args.input, output_path, args.include_archived)
    except Exception as e:
        print(f"錯誤: {e}", file=__import__('sys').stderr)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

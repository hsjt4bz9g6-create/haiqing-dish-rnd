"""
飞书多维表格工具
"""
import requests
from typing import List, Dict, Optional
from cozeloop.decorator import observe
from coze_workload_identity import Client


class FeishuBitableClient:
    """飞书多维表格客户端"""
    
    def __init__(self, app_token: str = None):
        self.base_url = "https://open.larkoffice.com/open-apis"
        self.timeout = 30
        self.access_token = self._get_access_token()
        self.app_token = app_token
    
    def _get_access_token(self) -> str:
        """获取飞书多维表格的租户访问令牌"""
        client = Client()
        access_token = client.get_integration_credential("integration-feishu-base")
        return access_token
    
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
    
    @observe
    def _request(self, method: str, path: str, params: dict = None, json_data: dict = None) -> dict:
        """发送HTTP请求"""
        try:
            url = f"{self.base_url}{path}"
            resp = requests.request(
                method, 
                url, 
                headers=self._headers(), 
                params=params, 
                json=json_data, 
                timeout=self.timeout
            )
            resp_data = resp.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"飞书API请求错误: {e}")
        
        if resp_data.get("code") != 0:
            raise Exception(f"飞书API错误: {resp_data}")
        
        return resp_data
    
    def search_base(self, query: str) -> dict:
        """搜索多维表格"""
        body = {
            "search_key": query,
            "docs_types": ["bitable"]
        }
        return self._request("POST", "/suite/docs-api/search/object", json_data=body)
    
    def list_tables(self, app_token: str) -> dict:
        """列出多维表格中的所有表"""
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables")
    
    def add_records(self, table_id: str, records: List[Dict]) -> dict:
        """批量添加记录"""
        if not self.app_token:
            raise ValueError("app_token is required")
        
        body = {"records": records}
        return self._request(
            "POST", 
            f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create",
            json_data=body
        )
    
    def search_records(self, table_id: str, filter_conditions: dict = None) -> dict:
        """搜索记录"""
        if not self.app_token:
            raise ValueError("app_token is required")
        
        body = {}
        if filter_conditions:
            body["filter"] = filter_conditions
        
        return self._request(
            "POST",
            f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search",
            json_data=body
        )
    
    def add_field(self, table_id: str, field_name: str, field_type: int = 1) -> dict:
        """添加字段"""
        if not self.app_token:
            raise ValueError("app_token is required")
        
        body = {
            "field_name": field_name,
            "type": field_type
        }
        return self._request(
            "POST",
            f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields",
            json_data=body
        )

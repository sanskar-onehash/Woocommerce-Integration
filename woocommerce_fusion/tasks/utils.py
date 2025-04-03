import traceback

import frappe
import requests
from woocommerce import API


class APIWithRequestLogging(API):
	"""WooCommerce API with Request Logging."""

	def _API__request(self, method, endpoint, data, params=None, **kwargs):
		"""Override _request method to also create a 'WooCommerce Request Log'"""
		result = None
		try:
			result = super()._API__request(method, endpoint, data, params, **kwargs)
			if not frappe.flags.in_test:
				frappe.enqueue(
					"woocommerce_fusion.tasks.utils.log_woocommerce_request",
					url=self.url,
					endpoint=endpoint,
					request_method=method,
					params=params,
					data=data,
					res=result,
					traceback="".join(traceback.format_stack(limit=8)),
				)
			return result
		except Exception as e:
			if not frappe.flags.in_test:
				frappe.enqueue(
					"woocommerce_fusion.tasks.utils.log_woocommerce_request",
					url=self.url,
					endpoint=endpoint,
					request_method=method,
					params=params,
					data=data,
					res=result,
					traceback="".join(traceback.format_stack(limit=8)),
				)
			raise e


def log_woocommerce_request(
	url: str,
	endpoint: str,
	request_method: str,
	params: dict,
	data: dict,
	res: requests.Response | None = None,
	traceback: str = None,
):
	request_log = frappe.get_doc(
		{
			"doctype": "WooCommerce Request Log",
			"user": frappe.session.user if frappe.session.user else None,
			"url": url,
			"endpoint": endpoint,
			"method": request_method,
			"params": frappe.as_json(params) if params else None,
			"data": frappe.as_json(data) if data else None,
			"response": f"{str(res)}\n{res.text}" if res is not None else None,
			"error": frappe.get_traceback(),
			"status": "Success" if res and res.status_code in [200, 201] else "Error",
			"traceback": traceback,
			"time_elapsed": res.elapsed.total_seconds() if res is not None else None,
		}
	)

	request_log.save(ignore_permissions=True)

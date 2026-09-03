frappe.provide("frappe.query_reports");

(() => {
	const REPORT = "General Ledger";
	const FIELDNAME = "ignore_err";
	const FLAG = "__nissi_ignore_err_default";

	// Add `default: 1` to the ignore_err filter of a General Ledger settings
	// object. Idempotent and safe to call repeatedly.
	function apply_default(settings) {
		if (!settings || settings[FLAG]) return settings;

		if (Array.isArray(settings.filters)) {
			const f = settings.filters.find((df) => df && df.fieldname === FIELDNAME);
			if (f) {
				f.default = 1;
				settings[FLAG] = true;
			}
		}
		return settings;
	}

	// Case 1: the report script is already loaded (e.g. opened once before this
	// file ran) -> patch it immediately.
	if (frappe.query_reports[REPORT]) {
		apply_default(frappe.query_reports[REPORT]);
	}

	// Case 2: intercept the moment ERPNext assigns the settings object, so the
	// default is present before the filters are built for the first time.
	let stored = frappe.query_reports[REPORT];
	try {
		Object.defineProperty(frappe.query_reports, REPORT, {
			configurable: true,
			enumerable: true,
			get() {
				return stored;
			},
			set(value) {
				stored = apply_default(value);
			},
		});
	} catch (e) {
		// If the property can't be redefined for any reason, fail quietly: the
		// report keeps working, just without the pre-ticked default.
		// eslint-disable-next-line no-console
		console.warn(
			"Nissi: could not set default for General Ledger 'ignore_err' filter",
			e
		);
	}
})();
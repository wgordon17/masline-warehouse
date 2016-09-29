(function () {
	var curr_module = '//<module_name>';
	var data = document.getElementById('data');

	//<module_code>

	if (mod === undefined) {
		var mod = new Function();
	}

	return {
		processResponse: function processResponse(server_data) {
			if (typeof server_data != 'object' || typeof server_data['data'] != 'object' ||
					!server_data.hasOwnProperty('action') || !server_data.hasOwnProperty('data')) {
				msg.error('Unknown response received for module', 'Ok');
				console.log('Unknown response received for module: ' + server_data);
				return;
			}
			var module_action = server_data['action'];
			var module_data = server_data['data'];
			switch(module_action) {
				case 'load-data':
					if (!module_data.hasOwnProperty('module-html')) {
						msg.error('Unknown data from server when loading html');
						console.log('Unknown data from server when loading html: ' + module_data);
					} else {
						main_app.setHeader(curr_module, module_data['data-title']);
						main_app.setHeaderNotes(module_data['header-note']);
						data.innerHTML = module_data['module-html'];
						paging.recalculate('data');
					}

					if (mod.hasOwnProperty('afterLoad')) {
						mod.afterLoad(module_data);
					}
					break;

				default:
					if (mod.hasOwnProperty('processResponse')) {
						mod.processResponse(module_action, module_data);
					}
			}
		},
		initialize: function initialize() {
			main_app.closeMenu();
			main_app.showAllButtons();
			main_app.hideButton(curr_module);
			main_app.setHeader(curr_module);
			main_app.setHeaderNotes();
			while (data.lastChild) {
				paging.recalculate('data');
				data.removeChild(data.lastChild);
			}
			if (mod.hasOwnProperty('initialize')) {
				mod.initialize();
			}
		}
	};
})();
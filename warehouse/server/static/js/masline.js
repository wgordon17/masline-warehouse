var msg = (function () {

	var msg_queue = [];
	var msg_shown = false;

	var icons = {
		error: new Image(),
		info: new Image(),
		override: new Image(),
		ask: new Image()
	};

	var help_imgs = {
		wifi_icon: new Image(),
		wifi_img: new Image(),
		reboot_img: new Image()
	};

	icons.error.src = '/static/images/icons/error.png';
	icons.info.src = '/static/images/icons/info.png';
	icons.ask.src = '/static/images/icons/ask.png';
	icons.override.src = '/static/images/icons/override.png';

	help_imgs.wifi_icon.src = '/static/images/wifi.png';
	help_imgs.wifi_img.src = '/static/images/toggle_wifi.png';
	help_imgs.reboot_img.src = '/static/images/reboot.png';

	function newMessage(type, message, buttons) {
		var message_element = document.createElement('div'),
			msg_icon_container = document.createElement('div'),
			msg_container = document.createElement('div'),
			button_container = document.createElement('div');
		// Fix up possible missing values
		if (type === undefined) {type = 'error';}
		if (message === undefined) {message =  type.charAt(0).toUpperCase() + type.substr(1).toLowerCase();}
		if (buttons === undefined) {buttons = ['Acknowledged'];}
		if (!(buttons instanceof Array)) {buttons = [buttons];}
		// Set up containers
		message_element.id = 'message';
		message_element.className = type;
		msg_icon_container.className = 'container';
		msg_container.className = 'message';
		button_container.className = 'buttons';
		// Message container
		createMessage(message, msg_container);
		// Buttons container
		for (var i = 0; i < buttons.length; i++) {
			if (type == 'ask') {
				createButton(buttons[i], button_container, function(){
					event.preventDefault();
					socket.send({
						'action': 'module',
						'data': {
							'action': 'question-response',
							'data': {'response': event.target.dataset.response}
						}
					});
					dismissMessage();
				});
			} else {
				createButton(buttons[i], button_container);
			}
		}
		// Add containers to element
		msg_icon_container.appendChild(icons[type]);
		msg_icon_container.appendChild(msg_container);
		message_element.appendChild(msg_icon_container);
		message_element.appendChild(button_container);
		// Sound off
		if (type == 'error') {
			play.error();
		} else {
			play.notify();
		}

		return message_element;
	}

	function createMessage(message, container) {
		var msg_node = document.createElement('h1');
		var txt_node = document.createTextNode(message);
		msg_node.appendChild(txt_node);
		container.appendChild(msg_node);
	}

	function createButton(button, container, event_function) {
		var button_node = document.createElement('button');
		main_app.attachButtonEvents(button_node);
		var text_node = document.createTextNode(button);
		if (event_function === undefined) {
			event_function = dismissMessage;
		}
		button_node.appendChild(text_node);
		button_node.dataset.response = button.toLowerCase();
		button_node.addEventListener('touchstart', event_function, true);
		button_node.addEventListener('click', event_function, true);
		container.appendChild(button_node);
	}

	function dismissMessage() {
		var message = document.getElementById('message');
		if (msg_queue.length > 0) {
			var msg_data = msg_queue.shift();
			if (msg_data.type != 'number' && msg_data.type != 'element') {
				var new_message = newMessage(msg_data.type, msg_data.message, msg_data.buttons);
				message.parentNode.replaceChild(new_message, message);
				document.getElementById('sliding-container').style.webkitFilter = 'blur(10px)';
				window.addEventListener('orientationchange', resizeText, true);
				resizeText();
			} else if (msg_data.type == 'number') {
				msg_shown = false;
				numbers.request_number(msg_data.message, msg_data.buttons);
			} else if (msg_data.type == 'element') {
				message.parentNode.replaceChild(msg_data.element, message);
				document.getElementById('sliding-container').style.webkitFilter = 'blur(10px)';
				window.addEventListener('orientationchange', resizeText, true);
			}
		} else {
			message.className = 'hide';
			msg_shown = false;
			window.removeEventListener('orientationchange', resizeText, true);
			document.getElementById('sliding-container').style.webkitFilter = '';
		}
	}

	function resizeText() {
		var msg = document.getElementById('message');
		//Check if images are loaded yet, if not, delay
		if (msg.getElementsByTagName('img')[0].getBoundingClientRect().height == 0) {
			setTimeout(resizeText, 100);
			return;
		}
		var message_container = msg.getElementsByClassName('message')[0];
		message_container.parentNode.style.alignItems = 'stretch';
		var text_container = message_container.firstChild;
		var h1_fontSize = 8;
		var h1_lineHeight = 9;
		var runs = 0.5;
		text_container.style.fontSize = '';
		text_container.style.lineHeight = '';
		var msg_height = message_container.getBoundingClientRect().height;
		var txt_height = text_container.getBoundingClientRect().height;
		while (txt_height > msg_height) {
			text_container.style.fontSize = (h1_fontSize - runs) + 'vmax';
			text_container.style.lineHeight = (h1_lineHeight - runs) + 'vmax';
			msg_height = message_container.getBoundingClientRect().height;
			txt_height = text_container.getBoundingClientRect().height;
			runs += 0.5;
		}
		message_container.parentNode.style.alignItems = '';
	}

	var wifi = (function() {
		var old_message = null;
		var wifi_shown = false;

		function createWifiMessage(reason) {
			var message_element = document.createElement('div'),
				msg_icon_container = document.createElement('div'),
				msg_container = document.createElement('div'),
				wifi_elem = document.createElement('div'),
				wifi_msg = document.createElement('h2'),
				help_msg = document.createElement('h2'),
				arrow = document.createElement('div');
			// Set containers
			message_element.id = 'message';
			msg_icon_container.className = 'container';
			msg_container.className = 'message';
			// Message container
			if (!navigator.onLine || reason == 'wifi') {
				createMessage('Connection Lost due to Wi-Fi issues', msg_container);
				// Wi-fi container
				help_imgs.wifi_icon.style.margin = 0;
				wifi_msg.textContent = 'Do you see this icon?';
				help_msg.textContent = 'If not, tap here for help!';
				wifi_elem.appendChild(wifi_msg);
				wifi_elem.appendChild(help_imgs.wifi_icon);
				wifi_elem.appendChild(help_msg);
				wifi_elem.className = 'wifi-container';
				arrow.className = 'arrow';
				wifi_elem.addEventListener('touchstart', showWifiHelp, true);
				wifi_elem.addEventListener('click', showWifiHelp, true);
				message_element.appendChild(wifi_elem);
				message_element.appendChild(arrow);
			} else {
				createMessage(reason, msg_container);
			}
			// Add containers to element
			msg_icon_container.appendChild(msg_container);
			message_element.appendChild(msg_icon_container);
			return message_element;
		}

		function showWifiHelp() {
			event.preventDefault();
			if (document.getElementById('wifi-help') == null) {
				var container = document.createElement('div'),
					large_arrow = document.createElement('div'),
					msg_part1 = document.createElement('h2'),
					msg_part2 = document.createElement('h2');
				container.id = 'wifi-help';
				large_arrow.className = 'large-arrow';
				msg_part1.textContent = '1. Pull down status bar here';
				msg_part2.textContent = '2. Tap indicated icon';
				container.appendChild(large_arrow);
				container.appendChild(msg_part1);
				container.appendChild(help_imgs.wifi_img);
				container.appendChild(msg_part2);
				document.getElementById('message').appendChild(container);
				setTimeout(function(){document.getElementById('wifi-help').style.webkitTransform = 'translate3d(0, -100%, 0)';}, 100);
				// Display "Didn't work" <dismiss> button after 5 seconds
				setTimeout(function(){
					var help_container = document.getElementById('wifi-help');
					var button = document.createElement('button');
					main_app.attachButtonEvents(button);
					button.textContent = 'Didn\'t help';
					button.dataset.dismiss = 'dismiss';
					button.addEventListener('touchstart', function(){
						event.preventDefault();
						help_container.style.webkitTransform = '';
						setTimeout(function(){var e = document.getElementById('wifi-help');e.parentNode.removeChild(e);}, 1000);
						showSecondWifiMessage();
					}, true);
					button.addEventListener('click', function(){
						event.preventDefault();
						help_container.style.webkitTransform = '';
						setTimeout(function(){var e = document.getElementById('wifi-help');e.parentNode.removeChild(e);}, 1000);
						showSecondWifiMessage();
					}, true);
					help_container.appendChild(button);
				}, 5000);
			}
		}

		function showSecondWifiMessage() {
			var msg_container = document.getElementById('message');
			var reboot_msg = document.createElement('h2');
			reboot_msg.appendChild(document.createTextNode('So, definitely not connected?'));
			reboot_msg.appendChild(document.createElement('br'));
			reboot_msg.appendChild(document.createTextNode('Tap here for last resort!'));
			reboot_msg.className = 'wifi-reboot';
			reboot_msg.addEventListener('touchstart', showWifiReboot, true);
			reboot_msg.addEventListener('click', showWifiReboot, true);
			msg_container.removeChild(msg_container.getElementsByClassName('wifi-container')[0]);
			msg_container.removeChild(msg_container.getElementsByClassName('arrow')[0]);
			msg_container.appendChild(reboot_msg);
		}

		function showWifiReboot() {
			event.preventDefault();
			if (document.getElementById('reboot-help') == null) {
				var container = document.createElement('div'),
					large_arrow = document.createElement('div'),
					msg_part1 = document.createElement('h2'),
					msg_part2 = document.createElement('h2');
				container.id = 'reboot-help';
				large_arrow.className = 'large-arrow';
				msg_part1.textContent = '1. Press and hold Power button on side';
				msg_part2.textContent = '2. Tap indicated icon';
				container.appendChild(large_arrow);
				container.appendChild(msg_part1);
				container.appendChild(help_imgs.reboot_img);
				container.appendChild(msg_part2);
				document.getElementById('message').appendChild(container);
				setTimeout(function(){document.getElementById('reboot-help').style.webkitTransform = 'translate3d(0, -100%, 0)';}, 100);
				window.addEventListener('orientationchange', fixRebootOrientation, true);
			}
		}

		function fixRebootOrientation() {
			var reboot = document.getElementById('reboot-help');
			if (reboot != null) {
				//noinspection JSUnresolvedVariable
				if (window.orientation == -90 || window.orientation == 180) {
					reboot.style.webkitTransform = 'translate3d(0, -100%, 0) rotate(180deg)';
				} else {
					reboot.style.webkitTransform = 'translate3d(0, -100%, 0)';
				}
			} else {
				window.removeEventListener('orientationchange', fixRebootOrientation, true);
			}
		}

		return {
			lost_connection: function lost_connection(reason) {
				document.getElementById('sliding-container').style.webkitFilter = 'blur(10px)';
				if (!wifi_shown) {
					var msg_elem = document.getElementById('message');
					if (!!msg_shown) {
						old_message = msg_elem;
						msg_elem.parentNode.replaceChild(createWifiMessage(reason), msg_elem);
					} else {
						msg_elem.parentNode.replaceChild(createWifiMessage(reason), msg_elem);
					}
					msg_shown = true;
					wifi_shown = true;
				}
			},
			connection_restored: function connection_restored() {
				if (socket.connected() && !!wifi_shown) {
					var msg_elem = document.getElementById('message');
					if (old_message != null) {
						msg_elem.parentNode.replaceChild(old_message, msg_elem);
					} else {
						msg_shown = false;
						msg_elem.className = 'hide';
						document.getElementById('sliding-container').style.webkitFilter = '';
					}
				}
				wifi_shown = false;
			}
		};
	})();

	var numbers = (function () {
		var value_hist = [];
		var curr_number;
		var undo_button;
		var add_buttons;
		var rep_buttons;
		var callback;

		function createNumberMessage(message) {
			var message_element = document.createElement('div'),
				msg_icon_container = document.createElement('div'),
				msg_container = document.createElement('div'),
				label_container = document.createElement('div'),
				undo = document.createElement('button'),
				qty_msg = document.createElement('h2'),
				done = document.createElement('button');
			main_app.attachButtonEvents(undo);
			main_app.attachButtonEvents(done);
			// Set containers
			message_element.id = 'message';
			msg_icon_container.className = 'container';
			msg_container.className = 'message';
			// Label container
			label_container.className = 'label-container';
			qty_msg.appendChild(document.createTextNode(message + ':'));
			// Undo button
			undo.appendChild(document.createTextNode('Undo'));
			undo.className = 'undo';
			undo.disabled = true;
			undo.addEventListener('touchstart', undoClick, true);
			undo.addEventListener('click', undoClick, true);
			// Done button
			done.appendChild(document.createTextNode('Done'));
			done.className = 'done';
			done.addEventListener('touchstart', doneClick, true);
			done.addEventListener('click', doneClick, true);
			// Add to label container
			label_container.appendChild(qty_msg);
			label_container.appendChild(undo);
			label_container.appendChild(done);
			// Message container
			createMessage('0', msg_container);
			curr_number = msg_container.getElementsByTagName('h1')[0];
			undo_button = undo;
			msg_icon_container.appendChild(label_container);
			msg_icon_container.appendChild(msg_container);
			message_element.appendChild(msg_icon_container);
			add_buttons = additiveNumberRow();
			rep_buttons = replacementNumberRow();
			message_element.appendChild(add_buttons);
			message_element.appendChild(rep_buttons);
			return message_element;
		}

		function additiveNumberRow() {
			var row = numberRow(),
				button_list = row.getElementsByTagName('button');
			row.classList.add('additive');
			// 1,5,10,15,20,25,50,100,500,1000
			button_list[0].textContent = '1';
			button_list[1].textContent = '5';
			button_list[2].textContent = '10';
			button_list[3].textContent = '15';
			button_list[4].textContent = '20';
			button_list[5].textContent = '25';
			button_list[6].textContent = '50';
			button_list[7].textContent = '100';
			button_list[8].textContent = '500';
			button_list[9].textContent = '1000';
			for (var i = 0; i < button_list.length; i++) {
				button_list[i].dataset.value = button_list[i].textContent;
				button_list[i].addEventListener('touchstart', additiveClick, true);
				button_list[i].addEventListener('click', additiveClick, true);
			}
			return row;
		}

		function replacementNumberRow() {
			var row = numberRow(),
				button_list = row.getElementsByTagName('button');
			button_list[0].textContent = '1';
			button_list[1].textContent = '2';
			button_list[2].textContent = '3';
			button_list[3].textContent = '4';
			button_list[4].textContent = '5';
			button_list[5].textContent = '6';
			button_list[6].textContent = '7';
			button_list[7].textContent = '8';
			button_list[8].textContent = '9';
			button_list[9].textContent = '0';
			for (var i = 0; i < button_list.length; i++) {
				button_list[i].dataset.value = button_list[i].textContent;
				button_list[i].addEventListener('touchstart', replacementClick, true);
				button_list[i].addEventListener('click', replacementClick, true);
			}
			return row;
		}

		function numberRow() {
			var numberRow = document.createElement('div'),
				total_buttons = 10,	// 0-9 or 1,5,10,15,20,25,50,100,500,1000
				new_button;
			numberRow.className = 'buttons';
			for (var i = 0; i < total_buttons; i++) {
				new_button = document.createElement('button');
				main_app.attachButtonEvents(new_button);
				new_button.className = 'minimized';
				numberRow.appendChild(new_button);
			}
			return numberRow;
		}

		function additiveClick() {
			event.preventDefault();
			if (event.target.disabled != true) {
				value_hist.push('' + curr_number.textContent);
				curr_number.textContent = (curr_number.textContent^0) + (event.target.dataset.value^0);
				if (undo_button.disabled == true) {
					undo_button.disabled = false;
				}
				checkLength();
			}
		}

		function replacementClick() {
			event.preventDefault();
			if (event.target.disabled != true) {
				value_hist.push(curr_number.textContent);
				if (curr_number.textContent == '0') {
					curr_number.textContent = event.target.dataset.value;
				} else {
					curr_number.textContent += event.target.dataset.value;
				}
				if (undo_button.disabled == true) {
					undo_button.disabled = false;
				}
				checkLength();
			}
		}

		function checkLength() {
			if (curr_number.textContent.length >= 13) {
				var add_button_list = add_buttons.getElementsByTagName('button'),
					rep_button_list = rep_buttons.getElementsByTagName('button');
				for (var i = 0; i < add_button_list.length; i++) {
					add_button_list[i].disabled = true;
					rep_button_list[i].disabled = true;
				}
			}
		}

		function undoClick() {
			if (!this.disabled) {
				event.preventDefault();
				if (curr_number.textContent.length == 13) {
					var add_button_list = add_buttons.getElementsByTagName('button'),
						rep_button_list = rep_buttons.getElementsByTagName('button');
					for (var i = 0; i < add_button_list.length; i++) {
						add_button_list[i].disabled = false;
						rep_button_list[i].disabled = false;
					}
				}
				curr_number.textContent = value_hist.pop();
				if (value_hist.length == 0) {
					this.disabled = true;
				}
			}
		}

		function doneClick() {
			event.preventDefault();
			var callback_qty = curr_number.textContent;
			setTimeout(callback, 100, callback_qty);
			value_hist = [];
			curr_number = null;
			undo_button = null;
			add_buttons = null;
			rep_buttons = null;
			callback = null;
			dismissMessage();
		}

		return {
			request_number: function request_number(message, buttons) {
				callback = new Function('value', 'socket.send({"action": "module", "data": {"action": "process-qty", "data": {"qty": value}}});');
				var msg_elem = document.getElementById('message');
				if (!!msg_shown) {
					msg_queue.push({'type': 'number', 'message': message, 'buttons': buttons});
				} else {
					// Flag captureKeys to ignore the scanner
					msg_shown = true;
					msg_elem.parentNode.replaceChild(createNumberMessage(message), msg_elem);
					document.getElementById('sliding-container').style.webkitFilter = 'blur(10px)';
				}
			}
		}
	})();

	var loader = (function() {
		var loading_shown = false;

		function showLoader() {
			var message_element = document.createElement('div'),
				msg_spinner_container = document.createElement('div'),
				loader_text = document.createElement('h2');
			// Set containers
			message_element.id = 'message';
			msg_spinner_container.className = 'loading';
			loader_text.appendChild(document.createTextNode('Loading'));
			msg_spinner_container.appendChild(loader_text);
			message_element.appendChild(msg_spinner_container);
			return message_element;
		}

		return {
			show_loading: function show_loading() {
				document.getElementById('sliding-container').style.webkitFilter = 'blur(10px)';
				if (!loading_shown) {
					var msg_elem = document.getElementById('message');
					if (!!msg_shown) {
						msg_queue.unshift({'element': msg_elem, 'type': 'element'});
						msg_elem.parentNode.replaceChild(showLoader(), msg_elem);
					} else {
						msg_elem.parentNode.replaceChild(showLoader(), msg_elem);
					}
					setTimeout(function() {
						var elem = document.querySelector('#message .loading');
						if (elem) {
							elem.classList.add('loading-animated');
						} else {
							loading_shown = false;
						}
					}, 50);
					msg_shown = true;
					loading_shown = true;
				}
			},
			done_loading: function done_loading() {
				if (!!loading_shown) {
					loading_shown = false;
					dismissMessage();
				}
			}
		};
	})();

	return (function() {
		var key_list = Object.keys(icons);
		var new_obj = {};
		for (var i = 0; i < key_list.length; i++) {
			new_obj[key_list[i]] = (function (curr_key) {
				return function (message, buttons) {
						var msg_elem = document.getElementById('message');
						if (!!msg_shown) {
							msg_queue.push({'type': curr_key, 'message': message, 'buttons': buttons});
						} else {
							// Flag captureKeys to ignore the scanner
							msg_shown = true;
							msg_elem.parentNode.replaceChild(newMessage(curr_key, message, buttons), msg_elem);
							document.getElementById('sliding-container').style.webkitFilter = 'blur(10px)';
							window.addEventListener('orientationchange', resizeText, true);
							resizeText();
						}
				};
			})(key_list[i]);
		}

		for (var value in wifi) {
			new_obj[value] = wifi[value];
		}
		for (value in numbers) {
			new_obj[value] = numbers[value];
		}
		for (value in loader) {
			new_obj[value] = loader[value];
		}

		new_obj['visible'] = function visible() {
			return (msg_shown == true);
		};

		return new_obj;
	})();
})();
var play = (function () {
	function BufferLoader(context, urlList) {
		this.context = context;
		this.urlList = urlList;
		this.buffers = {};
		this.total_initialized = 0;
	}
	BufferLoader.prototype.loadBuffer = function(url, name) {
		var request = new XMLHttpRequest();
		request.open('GET', url, true);
		request.responseType = 'arraybuffer';
		var loader = this;
		request.onload = function() {
			//noinspection JSValidateTypes
			loader.context.decodeAudioData(request.response, function(buffer) {
				if (!buffer) {
					msg.error('Error loading sound file');
					console.log('Error loading sound file: ' + url);
					return;
				}
				loader.buffers[name] = buffer;
				loader.total_initialized += 1;
			});
		};
		request.send();
	};
	BufferLoader.prototype.load = function() {
		for (var i = 0; i < this.urlList.length; i++) {
			var url = this.urlList[i];
			this.loadBuffer(url, url.substr(url.lastIndexOf('/') + 1, url.lastIndexOf('.') - url.lastIndexOf('/') - 1));
		}
	};

	// Fix up prefixing
	window.AudioContext = window.AudioContext || window.webkitAudioContext;
	var context = new AudioContext();
	var prefix = '/static/audio/';
	var sounds = new BufferLoader(context, [prefix + 'success.ogg', prefix + 'error.ogg', prefix + 'notify.ogg']);

	sounds.load();

	function playSound(buffer_name) {
		if (sounds.total_initialized != sounds.urlList.length) {
			setTimeout(play[buffer_name], 50);
		} else {
			var source = context.createBufferSource();
			try {
				source.buffer = sounds.buffers[buffer_name];
				source.connect(context.destination);
				source.start(0);
			} catch (e) {
				msg.error('Error playing sound');
				console.log('Error playing sound: ' + e);
			}
		}
	}

	return {
		success: function success() { playSound(arguments.callee.name) },
		error: function error() { playSound(arguments.callee.name) },
		notify: function notify() { playSound(arguments.callee.name) }
	};
})();
var main_app = (function () {
	var e = {
		sliding_container: document.getElementById('sliding-container'),
		menu_tab: document.getElementById('menu-tab'),
		heading: document.getElementById('heading'),
		module_buttons: document.getElementById('module-list').getElementsByTagName('button'),
		module_title: document.getElementById('module-title'),
		data_title: document.getElementById('data-title'),
		header_notes: document.getElementById('header-notes')
	};
	e['data_title_span'] = e.data_title.getElementsByTagName('span')[0];
	var values_captured = '';

	e['module_title'].addEventListener('touchstart', function(){
		event.preventDefault();
		socket.send({'action': 'module', 'data': {'action': 'reset-module', 'data': {}}});
	}, true);
	e['module_title'].addEventListener('click', function(){
		event.preventDefault();
		socket.send({'action': 'module', 'data': {'action': 'reset-module', 'data': {}}});
	}, true);

	e.menu_tab.addEventListener('touchstart', function(){event.preventDefault();e.sliding_container.classList.toggle('open');paging.recalculate('module-list');}, true);
	e.menu_tab.addEventListener('click', function(){event.preventDefault();e.sliding_container.classList.toggle('open');paging.recalculate('module-list');}, true);
	for(var button_index = 0; button_index < e.module_buttons.length; button_index++) {
		e.module_buttons[button_index].addEventListener('touchstart', function(){
			event.preventDefault();
			//noinspection JSUnresolvedVariable
			socket.send({'action': 'request-module', 'data': {'module': event.target.dataset.moduleName}});
		}, true);
		e.module_buttons[button_index].addEventListener('click', function(){
			event.preventDefault();
			//noinspection JSUnresolvedVariable
			socket.send({'action': 'request-module', 'data': {'module': event.target.dataset.moduleName}});
		}, true);
	}

	document.addEventListener('keypress', captureKeys, true);
	document.addEventListener('webkitvisibilitychange', detectScreenlock, true);

	function resizeTextWidth(element, sub_element) {
		var elem_rect = element.getBoundingClientRect(),
			sub_rect = sub_element.getBoundingClientRect();
		//Check if images are loaded yet, if not, delay
		if (sub_rect.width == 0) {
			setTimeout(resizeText, 100, element, sub_element);
			return;
		}
		var h1_fontSize = 8;
		var h1_lineHeight = 9;
		var runs = 0.5;
		element.style.fontSize = '';
		element.style.lineHeight = '';
		while (sub_rect.width > elem_rect.width) {
			element.style.fontSize = (h1_fontSize - runs) + 'vmax';
			element.style.lineHeight = (h1_lineHeight - runs) + 'vmax';
			elem_rect = element.getBoundingClientRect();
			sub_rect = sub_element.getBoundingClientRect();
			runs += 0.5;
		}
	}

	function findKeyframesRule(rule) {
		var ss = document.styleSheets;
		for (var i = 0; i < ss.length; i++) {
			for (var j = 0; j < ss[i].cssRules.length; j++) {
				if (ss[i].cssRules[j].type == window.CSSRule.WEBKIT_KEYFRAMES_RULE && ss[i].cssRules[j].name == rule) {
					return ss[i].cssRules[j];
				}
			}
		}
		return null;
	}

	function initializeMarquee(elem) {
		var elem_width = elem.getBoundingClientRect().width,
			keys = findKeyframesRule('marquee');
		for (var i = 0; i < keys.cssRules.length; i++) {
			keys.deleteRule(keys.cssRules[i].keyText);
		}
		keys.appendRule('0% {-webkit-transform: translate3d(100vw, 0, 0);}');
		keys.appendRule('100% {-webkit-transform: translate3d(-' + elem_width + 'px, 0, 0);}');
		return elem_width;
	}

	/*
		This function calculates how long it would take the specified element to cross from
		out-of-sight on the right to out-of-sight on the left, at a constant speed, regardless
		of element width

		elem_width:		  Pre-computed width of element that is travelling
		desired_time: How long the message should take from initially out-of-sight to just touching other
						edge of browser

		equation:
			W = time to cross screen (desired_time)
			x = how long to set the transition time for (return val)
			y = browser width (window.innerWidth)
			z = animated element width (elem_width)

				W ( y + z )
			x = ----------
			    	y

	 */
	function calcConstantSpeed(elem_width, desired_time) {
		return (desired_time * (window.innerWidth + elem_width)) / window.innerWidth
	}

	function captureKeys() {
		event.preventDefault();
		if (!msg.visible()) {
			var key = event.which;
			values_captured += String.fromCharCode(key.valueOf());
			//key: 13 = 'Enter'
			if (key === 13) {
				if (values_captured.length > 1) {
					socket.send({'action': 'module', 'data': {'action': 'unknown-value', 'data': {'value': values_captured.slice(0, -1)}}});
				}
				values_captured = '';
			}
		}
	}

	function detectScreenlock() {
		/*
		 *	Possible states
		 *		visible
		 *		hidden
		 *		prerender
		 */
		//noinspection JSUnresolvedVariable
		if (document.webkitVisibilityState != 'visible' && !!socket.connected()) {
			socket.close(1000, 'screen-locked');
		}
	}

	function displayInfo() {
		msg.info(this.textContent);
	}

	function attachEvents(elem) {
		elem.addEventListener('touchstart', buttonTouch, true);
		elem.addEventListener('touchend', buttonTouch, true);
		elem.addEventListener('touchcancel', buttonTouch, true);

		function buttonTouch() {
			switch (event.type) {
				case 'touchstart':
					this.classList.add('active');
					break;
				case 'touchend':
				case 'touchcancel':
					this.classList.remove('active');
					break;
			}
		}
	}

	return {
		setHeader: function setHeader(module_name, data_title) {
			e.module_title.textContent = module_name;
			if (data_title === undefined) {
				e.module_title.classList.remove('cornered');
				e.data_title_span.textContent = '';
				e.data_title.style.display = 'none';
			} else {
				e.module_title.classList.add('cornered');
				e.data_title_span.textContent = data_title;
				e.data_title.style.display = '';
				resizeTextWidth(e.data_title, e.data_title_span)
			}
		},
		closeMenu: function closeMenu() {
			e.sliding_container.classList.remove('open');
			paging.recalculate('module-list');
		},
		openMenu: function openMenu() {
			e.sliding_container.classList.add('open');
			paging.recalculate('module-list');
		},
		hideButton: function hideButton(module_name) {
			for(var button_index = 0; button_index < e.module_buttons.length; button_index++) {
				//noinspection JSUnresolvedVariable
				if (e.module_buttons[button_index].dataset.moduleName == module_name) {
					e.module_buttons[button_index].style.display = 'none';
				}
			}
			paging.recalculate('module-list');
		},
		showAllButtons: function showAllButtons() {
			for(var button_index = 0; button_index < e.module_buttons.length; button_index++) {
				e.module_buttons[button_index].style.display = '';
			}
			paging.recalculate('module-list');
		},
		attachButtonEvents: function attachButtonEvents(elem) {
			if (elem instanceof NodeList || elem instanceof HTMLCollection) {
				for (var i = 0; i < elem.length; i++) {
					attachEvents(elem[i]);
				}
			} else {
				attachEvents(elem);
			}
		},
		setHeaderNotes: function setHeaderNotes(notes) {
			var data_node = document.getElementById('data');
			e.header_notes.textContent = '';
			e.header_notes.style.display = 'none';
			data_node.style.height = '';
			data_node.style.marginTop = '';
			e.header_notes.removeEventListener('click', displayInfo, true);
			e.header_notes.removeEventListener('touchstart', displayInfo, true);
			if (notes !== undefined && notes != '') {
				e.header_notes.textContent = notes;
				e.header_notes.style.display = '';
				data_node.style.height = '77vh';
				data_node.style.marginTop = '8vh';
				var width = initializeMarquee(e.header_notes);
				e.header_notes.style.webkitAnimation = 'marquee ' + calcConstantSpeed(width, 10) + 's linear infinite';
				e.header_notes.addEventListener('click', displayInfo, true);
				e.header_notes.addEventListener('touchstart', displayInfo, true);
			}
		},
		checkVisibility: function checkVisibility() {
			detectScreenlock();
		}
	};
})();
var socket = (function() {
	var s;
	var host = 'ws://' + location.host + '/data';
	var module = null;
	var socket_opened = 0;
	var close_reasons = {
		undefined: "No reason provided",
		// 0 - 999 are reserved and will not be used
		1000: "JS called .close()",
		1001: "Browser closed connection",
		1002: "Protocol error",
		1003: "Received unknown data",
		// 1004 is reserved
		1005: "No status code provided; Typically self initiated .close()",
		1006: "Connection lost without an explicit .close()",
		1007: "Data was not of consistent type",
		1008: "Message violates policy",
		1009: "Message received was too big",
		1010: "Extensions not included in handshake",
		1011: "Server terminated because of unknown condition",
		// 1012 - 1014 are not listed
		1015: "TLS (encrypted) handshake failed",
		// 1016 - 1999 are reserved for future implementation
		// 2000 - 2999 are reserved for websocket extensions
		// 3000 - 3999 are reserved for frameworks
		// 4000 - 4999 are allowed for private usage
		4001: "Connection refused",
        4002: "Connection not found"
	};

	function createSocket() {
		msg.show_loading();
		s = new WebSocket(host);
		s.addEventListener('open', initializeSocket, true);
	}

	function initializeSocket() {
		socket_opened = new Date().getTime();
		s.addEventListener('message', socketMessage, true);
		s.addEventListener('close', socketClosed, true);
		main_app.checkVisibility();
	}

	function decodeMessage(data) {
		//noinspection JSValidateTypes,JSCheckFunctionSignatures
		var server_response = JSON.parse(event.data);
		if (typeof server_response != 'object' ||					// Ensure response is proper JSON object
					!server_response.hasOwnProperty('action') ||	// Ensure JSON has 'action' property
					!server_response.hasOwnProperty('data') ||		// Ensure JSON has 'data' property
					typeof server_response['data'] != 'object') {	// Ensure 'data' is also a proper JSON object
			msg.error('Unknown response received from server', 'Ok');
			console.log('Unknown response received from server: ' + server_response);
			return [];
		}
		return [server_response['action'], server_response['data']];
	}

	function socketMessage() {
		var decoded = decodeMessage(event.data);
		if (decoded.length != 2) {
			return;
		}
		var server_action = decoded[0];
		var server_data = decoded[1];

		switch(server_action) {
			case 'switch-module':
				if (!server_data.hasOwnProperty('module-js')) {
					msg.error('You\'re trying to change functions, but I can\'t understand what the server is sending');
					console.log('You\'re trying to change functions, but I can\'t understand what the server is sending: ' + server_data);
				} else {
					module = new Function('return ' + server_data['module-js'].trim())();
					//noinspection JSUnresolvedFunction
					module.initialize();
				}
				break;

			case 'message':
				if (!server_data.hasOwnProperty('type')) {
					msg.error('The server tried to display a message, but I was unable understand it');
					console.log('The server tried to display a message, but I was unable understand it: ' + server_data);
				} else {
					msg[server_data['type']](server_data['message'], server_data['buttons']);
					if (server_data['type'] == 'error' && server_data.hasOwnProperty('debug-log')) {
						console.log(server_data['message'] + ': ' + server_data['debug-log']);
					}
				}
				break;

			case 'module':
				if (!server_data.hasOwnProperty('action') || !server_data.hasOwnProperty('data')) {
					msg.error('The server tried to send some information, but I was unable to process it');
					console.log('The server tried to send some information, but I was unable to process it: ' + server_data)
				} else {
					//noinspection JSUnresolvedFunction
					module.processResponse(server_data);
					play.success();
				}
				break;

			case 'reset-module':
				if (module !== null) {
					module.initialize();
				}
				break;

			default:
				msg.error('The server is trying to initiate an unknown action');
				console.log('The server is trying to initiate an unknown action: ' + server_action);
		}
		msg.done_loading();
	}

	function socketClosed() {
		event.preventDefault();
		play.error();
		// server purposefully kicked you off!
		if (!!event.wasClean) {
			var closed_msg = '';
			// If open for less than 1 second, assume the user doesn't need to be notified and just redirect
			if ((event.timeStamp - socket_opened) < 1000 || event.reason == 'screen-locked') {closed_msg = 'Error connecting. Try again';}
			// The server will not send a 1005 close code, so assume 1005 codes are from javascript and no message is needed/available
			if (event.code != 1005) {closed_msg = 'Connection refused';}
			if (closed_msg != '') {closed_msg = '?msg=' + encodeURIComponent(closed_msg)}
			window.location.replace('login' + closed_msg);
		// A 'whoops' kick...the server is probably off or wifi is off
		} else {
			msg.lost_connection('Uh-oh, something\'s not right! Determining problem...');
			setTimeout(function() {msg.connection_restored();msg.lost_connection('Ah-ha! The server is down for maintenance');}, 4000);
			checkConnection();
		}
	}

	function checkConnection() {
		if (!!navigator.onLine) {
			var xhr = new XMLHttpRequest();
			xhr.open('GET', location.href, true);
			xhr.onreadystatechange = function () {
				if (event.target.readyState === 4) {
					if (event.target.status === 200) {
						window.location.replace('login');
					} else {
						setTimeout(checkConnection, 500);
					}
				}
			};
			xhr.send();
		} else {
			setTimeout(checkConnection, 500);
		}
	}

	createSocket();

	return {
		send: function send(data) {
			if (s.readyState == s.OPEN) {
				if (typeof data != 'object' || typeof data['data'] != 'object' ||
					!data.hasOwnProperty('action') || !data.hasOwnProperty('data')) {
					msg.error('Trying to send improperly formatted message to server', 'Ok');
					console.log('Trying to send improperly formatted message to server: ' + data);
					return;
				}
				try {
					msg.show_loading();
					s.send(JSON.stringify(data));
				} catch (e) {
					msg.error('Unknown error sending a message to server', 'Ok');
					console.log('Unknown error sending a message to server (' + arguments.callee.caller.name + '): ' + e);
				}
			} else {
				setTimeout(socket.send, 500, data);
			}
		},
		connected: function connected() {
			return (s.readyState == s.OPEN);
		},
		close: function close(code, reason) {
			if (s.readyState == s.OPEN) {
				if (s.bufferedAmount === 0) {
					s.close(code, reason);
				} else {
					setTimeout(socket.close, 500, code, reason);
				}
			}
		}
	};
})();
var paging = (function() {
	function PagedElement(node) {
		this.compass = {
			'horizontal': {
				'dir1':		'left',
				'dir2':		'right',
				'dir3':		'top',
				'dir4':		'bottom',
				'value1':	'width',
				'value2':	'height',
				'point1':	'x',
				'point2':	'y',
				'translate_start': 'translate3d(',
				'translate_end': 'px, 0px, 0px)',
				'touch1': 'clientX',
				'touch2': 'clientY',
				'avg': 'avg_width'
			},
			'vertical': {
				'dir1':		'top',
				'dir2':		'bottom',
				'dir3':		'left',
				'dir4':		'right',
				'value1':	'height',
				'value2':	'width',
				'point1':	'y',
				'point2':	'x',
				'translate_start': 'translate3d(0px, ',
				'translate_end': 'px, 0px)',
				'touch1': 'clientY',
				'touch2': 'clientX',
				'avg': 'avg_height'
			}
		};
		this.e = node;
		this.e.paging = {};
		this.p = this.e.parentNode;
		this.p.paging = {'threshold': 50};
		this.e.paging.p = this.p;
		this.p.paging.e = this.e;
		this.recalculate();
	}
	PagedElement.prototype.fillRectangle = function () {
		this.e.paging.rectangle = this.fillChildren();
		this.p.paging.rectangle = this.p.getBoundingClientRect();
	};
	PagedElement.prototype.recalculate = function() {
		this.fillRectangle();
		if (this.compareRectangles() != 'same') {
			var that = this;
			setTimeout(function() {that.recalculate();}, 50);
			return;
		}
		delete(this.p.paging.compass);
		if ((this.p.paging.rectangle.height + this.p.paging.threshold) >= this.e.paging.rectangle.height && this.p.paging.rectangle.width < (this.e.paging.rectangle.width + this.p.paging.threshold)) {
			/* Left <--> Right paging */
			this.p.paging.compass = this.compass.horizontal;
		} else if (this.p.paging.rectangle.height < (this.e.paging.rectangle.height + this.p.paging.threshold) && (this.p.paging.rectangle.width + this.p.paging.threshold) >= this.e.paging.rectangle.width) {
			/* Top <--> Bottom paging */
			this.p.paging.compass = this.compass.vertical;
		}
		if (!!this.p.paging.hasOwnProperty('compass')) {
			this.attachPaging();
		} else {
			this.removePaging();
		}
	};
	/* Ensures window has completed repainting */
	PagedElement.prototype.compareRectangles = function() {
		var ret_val;
		if (!this.e.paging.hasOwnProperty('last_rectangle') ||
				this.e.paging.last_rectangle.height != this.e.paging.rectangle.height ||
				this.e.paging.last_rectangle.width != this.e.paging.rectangle.width ||
				this.e.paging.last_rectangle.top != this.e.paging.rectangle.top ||
				this.e.paging.last_rectangle.right != this.e.paging.rectangle.right ||
				this.e.paging.last_rectangle.bottom != this.e.paging.rectangle.bottom ||
				this.e.paging.last_rectangle.left != this.e.paging.rectangle.left) {
			this.e.paging.last_rectangle = this.e.paging.rectangle;
			ret_val = 'incorrect';
		} else {
			delete(this.e.paging.last_rectangle);
			ret_val = 'same';
		}
		return ret_val;
	};
	/* Assumes all children are button elements of this.e */
	PagedElement.prototype.fillChildren = function() {
		var children = this.e.getElementsByTagName('button');
		var top = new Array(children.length),
			bottom = new Array(children.length),
			left = new Array(children.length),
			right = new Array(children.length),
			curr_rectangle, max_right, min_left, max_bottom, min_top,
			total_widths = 0,
			total_heights = 0;
		for (var i = 0; i < children.length; i++) {
			curr_rectangle = children[i].getBoundingClientRect();
			top[i] = (curr_rectangle.top);
			bottom[i] = (curr_rectangle.bottom);
			left[i] = (curr_rectangle.left);
			right[i] = (curr_rectangle.right);
			total_heights += curr_rectangle.height + 45;
			total_widths += curr_rectangle.width + 45;
		}
		max_right = Math.max.apply(null, right);
		min_left = Math.min.apply(null, left);
		max_bottom = Math.max.apply(null, bottom);
		min_top = Math.min.apply(null, top);
		/* '30' addition is provided to account for 15px margin on both ends */
		return {
			'width': (max_right - min_left) + 35,
			'height': (max_bottom - min_top) + 35,
			'top': min_top,
			'bottom': max_bottom,
			'left': min_left,
			'right': max_right,
			'avg_height': total_heights / children.length,
			'avg_width': total_widths / children.length
		};
	};
	PagedElement.prototype.attachPaging = function() {
		var left = this.p.paging.compass.dir1,
			right = this.p.paging.compass.dir2,
			left_class = 'continues-' + left,
			right_class = 'continues-' + right,
			width = this.p.paging.compass.value1,
			avg = this.p.paging.compass.avg;
		// Conditional takes advantage of width equaling 'height' in portrait layout
		this.p.paging.step = width == 'width' ? this.e.paging.rectangle[avg] : this.e.paging.rectangle[avg] * 2;
		/* Only apply arrows if uninitialized */
		if (this.e.style.webkitTransition == '') {
			if (this.p.paging.rectangle[left] <= this.e.paging.rectangle[left] && this.p.paging.rectangle[right] < this.e.paging.rectangle[right]) {
				/* Right arrow, no Left */
				this.p.classList.remove(left_class);
				this.p.classList.add(right_class);
			} else if (this.p.paging.rectangle[left] > this.e.paging.rectangle[left] && this.p.paging.rectangle[right] >= this.e.paging.rectangle[right]) {
				/* Left arrow, no Right */
				this.p.classList.add(left_class);
				this.p.classList.remove(right_class);
			} else if (this.p.paging.rectangle[left] > this.e.paging.rectangle[left] && this.p.paging.rectangle[right] < this.e.paging.rectangle[right]) {
				/* Left AND Right arrows */
				this.p.classList.add(left_class);
				this.p.classList.add(right_class);
			}
			this.e.style.webkitTransform = 'translate3d(0px, 0px, 0px)';
			this.e.style.webkitTransition = '-webkit-transform 0.5s';
		}
		this.p.addEventListener('touchend', this.handlePaging, true);
		this.p.addEventListener('touchcancel', this.handlePaging, true);
		this.p.addEventListener('contextmenu', this.handlePaging, true);
	};
	PagedElement.prototype.removePaging = function() {
		this.p.classList.remove('continues-left');
		this.p.classList.remove('continues-right');
		this.p.classList.remove('continues-top');
		this.p.classList.remove('continues-bottom');
		this.p.removeEventListener('touchend', this.handlePaging, true);
		this.p.removeEventListener('touchcancel', this.handlePaging, true);
		this.p.removeEventListener('contextmenu', this.handlePaging, true);
		this.e.style.webkitTransition = '';
		this.e.style.webkitTransform = 'translate3d(0px, 0px, 0px)';
	};
	/* EVENT FUNCTION */
	PagedElement.prototype.handlePaging = function() {
		if (this === event.target) {
			event.preventDefault();
			var left = this.paging.compass.dir1,
				right = this.paging.compass.dir2,
				width = this.paging.compass.value1,
				start = this.paging.compass.translate_start,
				end = this.paging.compass.translate_end,
				x;
			if (event.type == 'contextmenu') {
				x = event[this.paging.compass.point1];
			} else {
				x = event.changedTouches[0][this.paging.compass.touch1];
			}
			/* Ensure click is still over the underlying element */
			if (x >= this.paging.e.paging.rectangle[left] && x <= this.paging.e.paging.rectangle[right]) {
				this.removeEventListener('touchend', arguments.callee, true);
				this.removeEventListener('touchcancel', arguments.callee, true);
				this.removeEventListener('contextmenu', this.handlePaging, true);
				this.paging.e.addEventListener('webkitTransitionEnd', function() {
					event.preventDefault();
					this.removeEventListener('webkitTransitionEnd', arguments.callee, true);
					paging.recalculate(event);
				}, true);
				var offset_left = this.paging.e.paging.rectangle[left] - this.paging.rectangle[left],
					new_value_for_left_button = offset_left + this.paging.step, /* Positive direction */
					new_value_for_right_button = offset_left - this.paging.step; /* Negative direction */
				if (x < (this.paging.rectangle[width] / 2)) {
					/* LEFT button, move RIGHT(positive) */
					/* Threshold bounding */
					if (new_value_for_left_button >= -this.paging.threshold || event.type == 'contextmenu') {
						new_value_for_left_button = 0;
						this.classList.remove('continues-' + left);
					}
					this.classList.add('continues-' + right);
					this.paging.e.style.webkitTransform = start + (new_value_for_left_button) + end;
				} else if (x > (this.paging.rectangle[width] / 2))  {
					/* RIGHT button, move LEFT(negative */
					/* Threshold bounding */
					if (new_value_for_right_button <= (this.paging.rectangle[width] - this.paging.e.paging.rectangle[width]) + this.paging.threshold || event.type == 'contextmenu') {
						new_value_for_right_button = this.paging.rectangle[width] - this.paging.e.paging.rectangle[width];
						this.classList.remove('continues-' + right);
					}
					this.classList.add('continues-' + left);
					this.paging.e.style.webkitTransform = start + (new_value_for_right_button) + end;
				}
			}
		}
	};

	var paged_elements = {
		'data': document.getElementById('data'),
		'module-list': document.getElementById('module-list')
	};

	for (var element in paged_elements) {
		paged_elements[element] = new PagedElement(paged_elements[element]);
	}

	function resetAll() {
		for (var element in paged_elements) {
			paged_elements[element].removePaging();
		}
		for (element in paged_elements) {
			paged_elements[element].recalculate();
		}
	}

	var resize_timer = 0;
	window.addEventListener('resize', function() {
		clearTimeout(resize_timer);
		resize_timer = setTimeout(resetAll, 250);
	}, true);

	return {
		recalculate: function recalculate(event) {
			if (!!event.hasOwnProperty('target')) {
				paged_elements[event.target.id].recalculate();
			} else if (!!paged_elements.hasOwnProperty(event)) {
				paged_elements[event].recalculate();
			}
		}
	}

})();
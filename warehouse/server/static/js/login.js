(function() {
	var values_captured = '';

	document.addEventListener('keypress', captureKeys, true);
	document.addEventListener('load', checkURL, true);
	window.addEventListener('online', networkChange, true);
	window.addEventListener('offline', networkChange, true);

	function captureKeys() {
		event.preventDefault();
		var key = event.which;
		//key: 36 = '$'...ignore character for wakeups
		if (key !== 36) {
			values_captured += String.fromCharCode(key.valueOf());
			//key: 13 = 'Enter'
			if (key === 13) {
				if (values_captured.length > 1) {
					sendRequest(values_captured.slice(0, -1));
				}
				values_captured = '';
			}
		}

		function sendRequest(data) {
			setMessage('Logging in', false);
			var xhr = new XMLHttpRequest();
			xhr.addEventListener('readystatechange', xhrEvent);
			xhr.open('POST', location.href, true);
			xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
			try {
				xhr.send('badge-id=' + data);
			} catch (e) {
				xhr.abort();
				document.removeEventListener('keypress', captureKeys, true);
				testConnection();
			}
			function xhrEvent() {
				if (event.type == 'readystatechange') {
					var result = event.target;
					if (result.readyState == 4) {
						if (result.status === 200) {
							window.location.replace('/')
						} else {
							//Put some kind of error message up with xhr.response
							setMessage(result.statusText);
						}
					}
				}
			}
			function testConnection() {
				var xhr = new XMLHttpRequest();
				xhr.open('POST', location.href, false);
				try {
					xhr.send();
					setMessage(window.original_msg, false);
					document.addEventListener('keypress', captureKeys, true);
				} catch (e) {
					xhr.abort();
					setMessage('The server seems to be unavailable', false);
					setTimeout(testConnection, 1000);
				}
			}
		}
	}

	function checkURL() {
		window.original_msg = document.getElementById('login-message').textContent;
		// Redirects the page back to plain "login" when a query parameter is present
		// Handles login error messages
		if (window.location.search != '') {
			setTimeout(function(){window.location.replace('login');}, 2500);
		}
	}

	function networkChange() {
		if (navigator.onLine === false) {
			setMessage('It appears that you are offline', false);
			document.removeEventListener('keypress', captureKeys, true);
		} else {
			setMessage('Yay, you\'re back online!');
			document.addEventListener('keypress', captureKeys, true);
		}
	}

	function setMessage(msgStr, revert) {
		if (revert === undefined) {
			revert = true;
		}
		var msg = document.getElementById('login-message');
		msg.textContent = msgStr;
		if (msgStr == 'Logging in') {
			msg.classList.add('loading');
			msg.classList.add('loading-animated');
		} else {
			msg.classList.remove('loading');
			msg.classList.remove('loading-animated');
		}
		if (revert) {
			setTimeout(function () {
				document.getElementById('login-message').textContent = window.original_msg;
			}, 2500);
		}
	}
})();
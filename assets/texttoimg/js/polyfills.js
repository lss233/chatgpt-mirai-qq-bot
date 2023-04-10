Array.prototype.findIndex = Array.prototype.findIndex || function(callback) {
  if (this === null) {
    throw new TypeError('Array.prototype.findIndex called on null or undefined');
  } else if (typeof callback !== 'function') {
    throw new TypeError('callback must be a function');
  }
  var list = Object(this);
  // Makes sures is always has an positive integer as length.
  var length = list.length >>> 0;
  var thisArg = arguments[1];
  for (var i = 0; i < length; i++) {
    if ( callback.call(thisArg, list[i], i, list) ) {
      return i;
    }
  }
  return -1;
};

if (!String.prototype.endsWith) {
    String.prototype.endsWith = function (text) {
        return this.indexOf(text, this.length - text.length) !== -1;
    };
}

if (!String.prototype.startsWith) {
    String.prototype.startsWith = function (text) {
        return this.lastIndexOf(text, 0) === 0;
    };
}
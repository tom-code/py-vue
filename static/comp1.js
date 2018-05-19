

Vue.component('comp1', {
  data: function() {
    return {
      msg: 'none'
    }
  },
  created: function () {
    ws_url = 'ws://' + location.host + '/ws/1';
    this.ws = new WebSocket(ws_url, "1");
    this.ws.onopen = function (event) {
      console.log('ws opened')
    }
    this.ws.onclose = function (event) {
      console.log('ws closed')
    }
    self = this;
    this.ws.onmessage = function(event) {
      self.$data.msg = event.data;
      self.ws.send('hohoho');
    }
  },
    template: '<div> {{ msg }} </div>'
})

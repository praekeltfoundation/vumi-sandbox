// Demonstration App

api.log_info("From init!");

api.on_unknown_command = function(command) {
    // Called for any command that doesn't have an explicit
    // command handler.
    this.log_info("From unknown: " + command.cmd);
}

api.on_inbound_message = function(command) {
    var msg = "Processing inbound-message: " + command.msg.content;
    this.log_info(msg, function (reply) {
        this.log_info("Log successful: " + reply.success);
        this.done();
    });
}

api.on_inbound_event = function(command) {
    var msg = "Processing inbound-event: " + command.msg.event_type;
    this.log_info(msg, function (reply) {
        this.log_info("Log successful: " + reply.success);
        this.done();
    });
}

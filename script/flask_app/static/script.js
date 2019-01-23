var hover_emph = [];
var highlight_lock = false;
var last_sense_group = "";

$(document).ready(function() {
    $.get("/letters", function(data, status) {
        $("#letters").html(data);
    });

    $.get("/reduce_functions", function(data, status) {
        $("#reduce-functions").html(data);
        $("#reduce-functions input[type=radio]").change(function() {
            get_frames(
                $("#chosen-one").text()
            );
        })
        //Click on the first radio button - for 100% up to date with the model.
        var first_radio = $("#reduce-functions input[type=radio]:first");
        first_radio.attr("checked", true)
        get_frames($("#chosen-one").text());
    });
    handle_resizing();
})

window.onresize = handle_resizing;

function view_get_rf() {
    return $("#reduce-functions").find("input:checked").val();
}

function get_words(letter) {
    $.get("/words/" + letter, function(data, status){
        $("#words").html(data);
    })
}

function get_frames(word, reduce_function=null, modify_view=true, callback=null) {
    if (word == "") {
        return
    }
    if (reduce_function == null) {
        reduce_function = view_get_rf();
    }
    $("#chosen-one").text(word);
    var opt_rf = "";
    if (reduce_function != null) {
        opt_rf = "&rf=" + reduce_function;
    }
    $.get("/frames?hw=" + word + opt_rf, function(data, status) {
        $("#frames-area").html(data);
        $("#n-frames").text("število stavčnih vzorcev: " + $(".frame-div").length);

        // Add functor highlighting
        $(".functor-link")
            .mouseover(function() {
                highlight_linked($(this))
            })
            .mouseout(unhighlight_linked)
            .click(function() {
                toggle_highlight_lock($(this))
            });
        // modify sense information div
        if (modify_view) {
            $("#word-info-right").html("");
            $(".frame-sense-id").hide();
            $(".frame-sense-id").find("input").prop("disabled", true);
            $(".frame-sense-desc").hide();
            //$(".frame-sense-desc").find("input").prop("disabled", true);
            switch (reduce_function) {
                case "reduce_0":
                case "reduce_1":
                    break;
                case "reduce_3":
                    //ssj
                    $(".frame-sense-id").show();
                    $(".frame-sense-desc").show();
                    break;
                case "reduce_4":
                    //kmeans
                    $(".frame-sense-id").show();
                    break;
                case "reduce_5":
                    //user
                    user_input_menu(false); 
                    $(".frame-sense-id").show();
                    break;
            }
        }
        if (callback != null) {
            callback();
        }
    });
}

function handle_resizing() {
    $("#words").height( ($(document).height() - $("#words").position().top) * 0.95 );
}

function highlight_linked(dom_element) {
    if (highlight_lock) {
        return;
    }
    var frame_div = dom_element.parents(".frame-div");
    var frame_table = frame_div.find(".frame-table");
    var frame_sentences = frame_div.find(".frame-sentences");
    var classes = dom_element.attr("class").split(" ");
    classes.forEach(function(cls) {
        if (cls == "functor-link") {
            return
        }
        cls = cls.replace(".", "\\."); //escaping dots!
        var frame_table_matches = frame_table.find("." + cls);
        var frame_sentences_matches = frame_sentences.find("." + cls);
        if (frame_table_matches.length > 0 && frame_sentences_matches.length > 0) {
            var matches = $.merge(frame_table_matches, frame_sentences_matches);
            matches.addClass("functor-highlight");
            hover_emph.push(matches);
        }
    })
}

function unhighlight_linked() {
    if (highlight_lock) {
        return;
    }
    hover_emph.forEach(function(el) {
        el.removeClass("functor-highlight");
    })
    hover_emph = [];
}

function toggle_highlight_lock(dom_element) {
    if (
        hover_emph.len == 0 ||
        !dom_element.hasClass("functor-highlight")
    ) {
        return;
    }
    highlight_lock = !highlight_lock;
}

function helper_highlight_ssj_id(pdiv, ssj_ids) {
    hover_emph = []
    for (var i=0; i<ssj_ids.length; i++) {
        ssj_id = ssj_ids[i];
        ssj_id = ssj_id.replace(".", "\\.");
        ssj_id = "." + ssj_id;
        matches = pdiv.find(ssj_id).toArray();
        if (matches.length > 1) {
            hover_emph = matches;
            break;
        }
    }
    hover_emph.forEach(function(element) {
        $(element).css("color", "red");
    });
}

function helper_clear_highlight_ssj_id() {
    hover_emph.forEach(function(element) {
        $(element).css("color", "");
    });
    hover_emph = []
}

function toggle_frame_sentences(el, sign=null) {
    pdiv = el.parents(".frame-div");
    fs = pdiv.find(".frame-sentences");
    sign_element = pdiv.find(".sign-element");
    if ((sign == "+") || (sign_element.text() == "[+]")) {
        sign_element.text("[-]");
        fs.show();
    } else {
        sign_element.text("[+]");
        fs.hide();
    }
}

function user_input_menu(new_entries) {
    if (new_entries) {
        var tmp_sense_group = $("#word-info-right").find("option:selected").text();
        if (tmp_sense_group != "-- izberi --") {
            last_sense_group = tmp_sense_group;
        }
        $("#word-info-right").html(
            "<input type=text name='sense_group' \
            placeholder='ime skupine pomenov' value='" + last_sense_group + "'></input>"
        );
        $("#word-info-right").append(
            "<button onclick='user_input_finish(false)'>prekliči</button>"
        )
        $("#word-info-right").append(
            "<input name='sense_passwd' \
            type=password placeholder='geslo' value='" + getCookie("sense_passwd") + "'></input>"
        )
        $("#word-info-right").append(
            "<button onclick='user_input_finish(true)'>shrani</button>"
        )
        get_frames($("#chosen-one").text(), "reduce_0", false, function() {
            $(".frame-sense-id").find("input")
                .prop("disabled", false)
                .val("");
            $(".frame-sense-id").show();
            //$(".frame-sense-desc").find("input").prop("disabled", true);
            $(".frame-sense-desc").hide();
            toggle_frame_sentences($(".frame-sense"), "+");
            //fill input fields with known sense_ids
            $.get("/get_sense_ids?collname=user_senses&hw=" + 
                $("#chosen-one").text() +
                "&sg=" + last_sense_group, function(data, status) {
                    data = JSON.parse(data);
                    $(".frame-div").each(function(idx, el) {
                        var jqel = $(el);
                        var ssj_id = jqel.find(".frame-hw-id").text();
                        if (ssj_id in data) {
                            jqel.find("input[name='sense_id']").val(data[ssj_id]);
                        }
                    });
                });
        });
    } else {
        $.get("/user_sense_groups/" + $("#chosen-one").text(), function(data, status){
            $("#word-info-right").html(data);
            $("#word-info-right").append(
                "<button onclick='user_input_menu(true)'>novi pomeni</button>"
            )
        });
    }
}

function user_input_finish(save) {
    if (save) {
        var sense_group = $("input[name='sense_group']").val().applyXSSprotection();
        var sense_passwd = $("input[name='sense_passwd']").val().applyXSSprotection();
        setCookie("sense_passwd", sense_passwd, 1);
        last_sense_group = sense_group;
        if (sense_group == "") {
            user_input_finish(false);
            return;
        }
        sense_data = {
            "headword": $("#chosen-one").text(),
            "sense_group": sense_group,
            "sense_passwd": sense_passwd,
            "entries": {},
        }
        $(".frame-div").each(function(index){
            var sense_id = $(this).find("input[name='sense_id']").val().applyXSSprotection();
            if (sense_id === "None") {
                return;
            }
            var frame_data = {};
            ssj_id = $(this).find(".frame-hw-id").text();
            sense_data["entries"][ssj_id] = sense_id;
        });
        if (Object.keys(sense_data["entries"]).length > 0) {
            $.ajax({
                method: "POST",
                url: "/user_senses",
                data: JSON.stringify(sense_data),
                async: false,
                complete: function() {
                    pick_sense_group(sense_group);
                }
            });
        }
        //pick_sense_group(sense_group);
    }
    user_input_menu(false);
    get_frames($("#chosen-one").text());
}

function pick_sense_group(sense_group, gf=false) {
    last_sense_group = sense_group;
    $.get("/pick_sense_group/" + sense_group, function(){
	    if (gf) {
		get_frames($("#chosen-one").text());
	    }
    });
}

String.prototype.applyXSSprotection = function(){
    return this.replace(/</g, "&lt;").replace(/>/g, "&gt;");
};

function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

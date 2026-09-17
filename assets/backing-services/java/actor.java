package com.example.deliverystarter.application.ports.events;

/**
 * Who or what caused an event, recorded on every one of them so the log answers "who did this".
 *
 * @param kind what sort of actor this is — a staff user, a customer, a scheduled job
 * @param id that actor's stable identifier within its kind
 */
public record Actor(String kind, String id) {
}

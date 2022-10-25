#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import csv
import os
import time
import configparser

import inputs
import mido


NOTES_PER_OCTAVE = 12
DEFAULT_VELOCITY = 80


def build_note_dictionaries(note_names, add_octave_no=True):
	C0_MIDI_NO = 12 # Plus basse note sur les pianos est La 0, mais on va commencer à générer les noms sur Do 0

	midi_to_name = {}
	name_to_midi = {}
	# Pour chaque octave de 0 à 8 (inclus). On va générer tout l'octave 8, même si la dernière note du piano est Do 8
	for octave in range(8+1):
		# Pour chaque note de l'octave
		for note in range(NOTES_PER_OCTAVE):
			# Calculer le numéro MIDI de la note et ajouter aux deux dictionnaires
			midi_no = C0_MIDI_NO + octave * NOTES_PER_OCTAVE + note
			# Ajouter le numéro de l'octave au nom de la note si add_octave_no est vrai
			full_note_name = note_names[note] + (str(octave) if add_octave_no else "")
			midi_to_name[midi_no] = full_note_name
			# Garder les numéros de notes dans name_to_midi entre 0 et 11 si add_octave_no est faux
			name_to_midi[full_note_name] = midi_no if add_octave_no else midi_no % NOTES_PER_OCTAVE
	return midi_to_name, name_to_midi

def send_note_on(note_name, name_to_midi, midi_outputs):
	msg = mido.Message("note_on", note=name_to_midi[note_name], velocity=DEFAULT_VELOCITY)
	for o in midi_outputs:
		o.send(msg)

def send_note_off(note_name, name_to_midi, midi_outputs):
	msg = mido.Message("note_off", note=name_to_midi[note_name])
	for o in midi_outputs:
		o.send(msg)

def build_note_callbacks(note_name, name_to_midi, midi_outputs):
	# Construire des callbacks pour bouton appuyé et relâché
	def action_fn_pressed():
		send_note_on(note_name, name_to_midi, midi_outputs)
	def action_fn_released():
		send_note_off(note_name, name_to_midi, midi_outputs)
	return action_fn_pressed, action_fn_released

def build_chord_callbacks(chord, chord_notes, name_to_midi, midi_outputs):
	# Construire des callbacks pour bouton appuyé et relâché
	def action_fn_pressed():
		for note in chord_notes[chord]:
			send_note_on(note, name_to_midi, midi_outputs)
	def action_fn_released():
		for note in chord_notes[chord]:
			send_note_off(note, name_to_midi, midi_outputs)
	return action_fn_pressed, action_fn_released

def build_custom_action_callbacks(action_name, custom_actions, midi_outputs):
	# Construire des callbacks pour bouton appuyé et relâché
	pressed, released = None, None
	if True in custom_actions[action_name] and custom_actions[action_name][True] is not None:
		def action_fn_pressed():
			custom_actions[action_name][True](midi_outputs)
		pressed = action_fn_pressed
	if False in custom_actions[action_name] and custom_actions[action_name][False] is not None:
		def action_fn_released():
			custom_actions[action_name][False](midi_outputs)
		released = action_fn_released
	return pressed, released

def load_input_mappings(filename, name_to_midi, chord_notes, midi_outputs, custom_actions={}):
	config = configparser.ConfigParser()
	config.read(filename)
	gamepad_section = config["gamepad"]

	mappings = {}
	for gamepad_input in gamepad_section:
		action_name = gamepad_section[gamepad_input]
		# Construire des callbacks pour l'action appropriée et l'ajouter au mapping.
		pressed, released = None, None
		if action_name in name_to_midi:
			pressed, released = build_note_callbacks(action_name, name_to_midi, midi_outputs)
		elif action_name in chord_notes:
			pressed, released = build_chord_callbacks(action_name, chord_notes, name_to_midi, midi_outputs)
		elif action_name in custom_actions:
			pressed, released = build_custom_action_callbacks(action_name, custom_actions, midi_outputs)
		mappings[gamepad_input] = {True: pressed, False: released}

	return mappings


def main():
	gamepad = inputs.devices.gamepads[0]
	midi_outputs = (mido.open_output("UM-ONE 3"), mido.open_output("UnPortMIDI 4"))
	midi_input = mido.open_input("UM-ONE 0")

	notes_data = json.load(open("notes.json", "r", encoding="utf-8"))
	note_names = notes_data["solfeggio_names"]
	midi_to_name, name_to_midi = build_note_dictionaries(note_names)
	chords = notes_data["chords"]

	def foo0(midi_outputs):
		print("henlo")
	def foo1(midi_outputs):
		print("k bye")
	def sustain_on(midi_outputs):
		msg = mido.Message("control_change", channel=0, control=64, value=127)
		for o in midi_outputs:
			o.send(msg)
	def sustain_off(midi_outputs):
		msg = mido.Message("control_change", channel=0, control=64, value=0)
		for o in midi_outputs:
			o.send(msg)

	custom_actions = {
		"foo": {True: foo0, False: foo1},
		"sustain": {True: sustain_on, False: sustain_off}
	}

	mappings = load_input_mappings("input.ini", name_to_midi, chords, midi_outputs, custom_actions)

	while True:
		for e in gamepad.read():
			btn = e.code.lower()
			pressed = bool(e.state)
			if btn in mappings:
				callbacks = mappings[btn]
				if pressed in callbacks and callbacks[pressed] is not None:
					mappings[btn][pressed]()
				print(btn, pressed)

if __name__ == "__main__":
	main()

----------------
-- TSP PROGRAM FOR PERFORMING TRANSFER SWEEPS
-- Sweeps over gate voltage and measures channel current

-- INPUT sweep start and end points with ABSOLUTE step size


-------- PARAMETERS --------
Vds = 0.2

VgStart = -60
VgEnd = 60
VgStep = 1

----- Device configuration -----
-- smua is connected to the gate 
-- smub is connected to the drain-source

-------- MAIN PROGRAM --------
reset()
display.clear()

-- Beep in excitement
beeper.beep(1, 600)

-- Clear buffers
smub.nvbuffer1.clear()
smua.nvbuffer1.clear()
-- Prepare buffers
smub.nvbuffer1.collectsourcevalues = 1
smua.nvbuffer1.collectsourcevalues = 1
format.data = format.ASCII
smub.nvbuffer1.appendmode = 1
smua.nvbuffer1.appendmode = 1
smub.measure.count = 1
smua.measure.count = 1


-- smua setup -- Gate control
smua.measure.delayfactor = 0.05
smua.measure.nplc = 5 -- integration time
-- smua.measure.rangei = 1e-8 -- current measurement range
smua.measure.autorangei = smua.AUTORANGE_ON
smua.source.func = smua.OUTPUT_DCVOLTS
smua.source.limiti = 1e-8
smua.sense = smua.SENSE_LOCAL
smua.source.autorangev = smua.AUTORANGE_ON -- auto range for v source

-- smub setup
smub.measure.delayfactor = 0.05 -- seconds
smub.measure.nplc = 5
smub.source.func = smub.OUTPUT_DCVOLTS
smub.sense = smub.SENSE_LOCAL
smub.source.autorangev = smub.AUTORANGE_ON
smub.measure.autorangei = smub.AUTORANGE_ON -- auto range for current measuerment
smub.source.limiti = 1e-5 -- compliance for current
-- smub.measure.rangei = 10e-5


--DISPLAY settings
display.smub.measure.func = display.MEASURE_DCAMPS
display.smua.measure.func = display.MEASURE_DCAMPS
display.screen = display.SMUA_SMUB

-- MEASUREMENT ROUTINE

smub.source.levelv = Vds -- smub is fixed voltage
smub.source.output = smub.OUTPUT_ON

-- slow ramp to starting voltage
smua.source.levelv = 0
smua.source.output = smua.OUTPUT_ON
Vg = 0
while Vg > VgStart do
    Vg = Vg - 1
    smua.source.levelv = Vg
    delay(0.005)
end

Vg = VgStart
delay(1) -- wait for things to settle before starting the full sweep

-- Forward Vg scan
if VgStart < VgEnd then
    while Vg <= VgEnd do
        smua.source.levelv = Vg
        -- smua.source.output = smua.OUTPUT_ON
        -- delay(0.05)
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
	    if math.mod(math.floor(Vg + 0.5), 10) == 0 then
            print("@@" .. smua.measure.v() .. "," .. smua.measure.i() .. "," .. smub.measure.v() .. "," .. smub.measure.i())
        end
        

        -- smua.source.output = smua.OUTPUT_OFF
        Vg = Vg + VgStep
    end

-- Reverse scan
elseif VgStart > VgEnd then
    while Vg >= VgEnd do
        smua.source.levelv = Vg
        -- smua.source.output = smua.OUTPUT_ON
        -- delay(0.05)
        smua.measure.i(smua.nvbuffer1)
        smub.measure.i(smub.nvbuffer1)
        if math.mod(math.floor(Vg + 0.5), 10) == 0 then
            print("@@" .. smua.measure.v() .. "," .. smua.measure.i() .. "," .. smub.measure.v() .. "," .. smub.measure.i())
        end
        


        -- smua.source.output = smua.OUTPUT_OFF
        Vg = Vg - VgStep
    end

else
    error("Invalid sweep parameters.")
end

smub.source.output = smub.OUTPUT_OFF
smua.source.output = smua.OUTPUT_OFF
waitcomplete()
print("EE")
-------- END --------
